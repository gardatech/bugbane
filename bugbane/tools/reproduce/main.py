# Copyright 2022 Garda Technologies, LLC. All rights reserved.
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
"""

from typing import Dict

import os
import sys
import shlex
import shutil

from bugbane.modules.fuzz_data_suite import FuzzDataSuite, FuzzDataError
from bugbane.modules.file_utils import dump_dict_as_json
from bugbane.modules.log import get_first_logger

from .args import exit_on_bad_args, parse_args

from .harvester import Harvester, HarvesterError


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    exit_on_bad_args(args)
    log = get_first_logger(__name__, verbosity_level=args.verbose)

    if shutil.which("gdb") is None:
        sys.exit("ERROR: gdb not found in path")

    if args.run_mode == "suite":
        try:
            suite, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.suite)
            src_path = bane_vars.get("src_root")
            if not src_path:
                raise FuzzDataError("no src_root in configuration file")

            fuzz_sync_dir = bane_vars.get("fuzz_sync_dir")
            if not src_path:
                raise FuzzDataError("no fuzz_sync_dir in configuration file")

            fuzzer_type = bane_vars.get("fuzzer_type")
            if not src_path:
                raise FuzzDataError("no fuzzer_type in configuration file")

            reproduce_specs: Dict[str, Dict[str, str]] = bane_vars.get(
                "reproduce_specs"
            )
            if not src_path:
                raise FuzzDataError("no reproduce_specs in configuration file")

            fuzz_type_dir = [fuzzer_type + ":" + fuzz_sync_dir]
            builds = [
                binary_path + ":" + subdir
                for binary_path, subdir in reproduce_specs[fuzzer_type].items()
            ]
            reproduce_specs = [fuzz_type_dir + builds]

            run_args = shlex.split(bane_vars.get("run_args") or "")
            run_env = bane_vars.get("run_env") or {}
            results_file_path = os.path.join(args.suite, "bb_results.json")
        except (FuzzDataError, KeyError, AttributeError) as e:
            log.error("Wasn't able to load fuzz data suite %s: %s", args.suite, e)
            return 1
    else:
        src_path = args.src_path
        run_args = args.program[1:]  # skip binary itself
        run_env = {}
        reproduce_specs = args.spec
        results_file_path = args.output

    harvester = Harvester()
    harvester.set_src_path_base(src_path)
    harvester.set_run_args(run_args)
    harvester.set_specs(reproduce_specs)

    harvester.set_num_reruns(args.num_reruns)
    harvester.set_use_abspath(args.abspath)
    harvester.set_hang_timeout(args.hang_timeout)

    reproduce_run_env = {
        "UBSAN_OPTIONS": "print_stacktrace=1:allocator_may_return_null=1:detect_stack_use_after_return=1",
        "ASAN_OPTIONS": "allocator_may_return_null=1:detect_stack_use_after_return=1",
    }

    # run_env from file is more important than defaults
    if run_env:
        reproduce_run_env.update(run_env)

    reproduce_run_env.update({"LANG": "C"})  # for gdb
    harvester.set_run_env(reproduce_run_env)

    log.debug("harvester init complete")

    try:
        result = harvester.collect_fuzzing_results()
    except HarvesterError as e:
        log.error("during reproduce: %s", e)
        return 1

    dump_dict_as_json(results_file_path, result)

    log.info(
        "Saved stats and %d issue cards to %s",
        len(result["issue_cards"]),
        results_file_path,
    )
    log.info("[+] Reproducing complete")

    return 0
