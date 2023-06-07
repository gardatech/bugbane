# Copyright 2022-2023 Garda Technologies, LLC. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Originally written by Valery Korolyov <fuzzah@tuta.io>

"""
1. Load fuzzer stats
2. Enumerate user provided directories
3. Run user provided binaries on samples from previous step (simple + gdb)
4. Collect flaw information (simple, sanitizer stack trace, gdb stack trace)
5. Generate bb_results.json
6. Save bug samples
"""

from typing import Dict, List, Optional

import os
import sys
import shlex
import shutil

from bugbane.modules.fuzz_data_suite import FuzzDataSuite, FuzzDataError
from bugbane.modules.file_utils import dump_dict_as_json
from bugbane.modules.log import get_verbose_logger

from .args import exit_on_bad_args, parse_args

from .harvester import Harvester, HarvesterError
from .bugsamplesaver import BugSampleSaver, BugSampleSaverError


def dict_to_reproduce_specs(
    fuzz_sync_dir: Optional[str],
    reproduce_specs: Optional[Dict[str, Dict[str, List[str]]]],
) -> List[List[str]]:
    """
    Convert "reproduce specs" dictionary to list of lists of strings.
    Output format is the same as used by ArgumentParser in manual run mode.
    Raise FuzzDataError if required arguments are empty or None.

    Expected input:
    ```
    fuzz_sync_dir="out",
    reproduce_specs={
        "AFL++": {
            "./basic/app": ["app1", "app2", "app3"],
            "./asan/app": ["app4"]
        }
    }
    ```
    For that input the output would be:
    [
        [
            "AFL++:out",
            "./basic/app:app1",
            "./basic/app:app2",
            "./basic/app:app3",
            "./asan/app:app4"
        ]
    ]
    """
    if not fuzz_sync_dir:
        raise FuzzDataError("no fuzz_sync_dir in configuration file")

    if not reproduce_specs:
        raise FuzzDataError("no reproduce_specs in configuration file")

    result: List[str] = []

    try:
        for fuzzer_type, spec in reproduce_specs.items():
            result.append(fuzzer_type + ":" + fuzz_sync_dir)
            for binary, subdirs in spec.items():
                result.extend(binary + ":" + subdir for subdir in subdirs)
    except AttributeError as e:  # no method .items() -> bad input json
        raise FuzzDataError("invalid reproduce specs") from e

    return [result]


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    exit_on_bad_args(args)
    log = get_verbose_logger(__name__, verbosity_level=args.verbose)

    log.info("[*] BugBane reproduce tool")

    if shutil.which("gdb") is None:
        sys.exit("ERROR: gdb not found in path")

    if args.run_mode == "suite":
        try:
            _, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.suite)
            src_path = bane_vars.get("src_root")
            if not src_path:
                raise FuzzDataError("no src_root in configuration file")

            fuzzer_type = bane_vars.get("fuzzer_type")
            if not fuzzer_type:
                raise FuzzDataError("no fuzzer_type in configuration file")

            reproduce_specs_dict: Optional[
                Dict[str, Dict[str, List[str]]]
            ] = bane_vars.get("reproduce_specs")

            fuzz_sync_dir = bane_vars.get("fuzz_sync_dir")
            reproduce_specs: List[List[str]] = dict_to_reproduce_specs(
                fuzz_sync_dir, reproduce_specs_dict
            )

            run_args = shlex.split(bane_vars.get("run_args") or "")
            run_env = bane_vars.get("run_env") or {}
            results_file_path = os.path.join(args.suite, "bb_results.json")
            bug_samples_dir = os.path.join(args.suite, "bug_samples")
        except (FuzzDataError, KeyError, AttributeError) as e:
            log.error(
                "Wasn't able to load fuzz data suite %s. %s: %s",
                args.suite,
                e.__class__.__name__,
                e,
            )
            return 1
    else:
        src_path = args.src_path
        run_args = args.program[1:]  # skip binary itself
        run_env = {}
        reproduce_specs = args.spec
        results_file_path = args.output
        bug_samples_dir = args.bug_samples_dir

    harvester = Harvester()
    harvester.set_src_path_base(src_path)
    harvester.set_run_args(run_args)
    harvester.set_specs(reproduce_specs)

    harvester.set_num_reruns(args.num_reruns)
    harvester.set_use_abspath(args.abspath)
    harvester.set_hang_reproduce_limit(args.hang_reproduce_limit)
    harvester.set_hang_timeout(args.hang_timeout)

    reproduce_run_env = {
        "UBSAN_OPTIONS": "print_stacktrace=1:allocator_may_return_null=1",
        "ASAN_OPTIONS": "allocator_may_return_null=1",
    }

    # run_env from file is more important than defaults
    if run_env:
        reproduce_run_env.update(run_env)

    reproduce_run_env.update({"LANG": "C"})  # for gdb
    harvester.set_run_env(reproduce_run_env)

    log.debug("harvester init complete")

    try:
        results = harvester.collect_fuzzing_results()
    except HarvesterError as e:
        log.error("during reproduce: %s", e)
        return 1

    bss = BugSampleSaver()
    try:
        bss.save_bug_samples(results, bug_samples_dir)
    except BugSampleSaverError as e:
        log.error("while saving bug samples: %s", e)
        return 1

    dump_dict_as_json(results_file_path, results)

    log.info(
        "Saved stats and %d issue cards to %s",
        len(results["issue_cards"]),
        results_file_path,
    )
    log.info("[+] Reproducing complete")

    return 0
