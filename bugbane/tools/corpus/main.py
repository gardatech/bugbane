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
Tool for importing input samples and exporting resulting samples
"""

import os
import shutil
import sys
import shlex
import tempfile

from bugbane.modules.log import get_first_logger
from bugbane.modules.fuzz_data_suite import FuzzDataError, FuzzDataSuite
from bugbane.modules.build_type import BuildType
from bugbane.modules.builds import BuildDetectionError, detect_builds

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo

from .minimizers.minimizer import MinimizerError, MinimizerFileAction
from .minimize_tools import (
    deduplicate_by_hashes,
    deduplicate_by_tool,
    sync_files_by_names,
)

from .args import parse_args


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_first_logger(__name__, args.verbose)

    minimizing_tool = None

    if args.run_mode == "suite":
        try:
            suite, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.suite)
            tested_binary_path = bane_vars.get("tested_binary_path") or None

            builds = detect_builds(args.suite, tested_binary_path)

            tool_minimizer_build_priority = [
                BuildType.LAF,
                BuildType.BASIC,
                BuildType.UBSAN,
                BuildType.CFISAN,
                BuildType.ASAN,
                BuildType.LSAN,
                BuildType.COVERAGE,
                BuildType.MSAN,
                BuildType.TSAN,
            ]
            app = None
            for bt in tool_minimizer_build_priority:
                if bt in builds:
                    app = builds[bt]
                    break

            run_args = shlex.split(bane_vars.get("run_args") or "")
            fuzzer_type = bane_vars.get("fuzzer_type")

            storage = os.path.join(
                args.storage, "samples"
            )  # TODO: use correct directory structure
            tmpdir_prefix = args.suite

            fuzzer_info: FuzzerInfo = FuzzerInfoFactory.create(fuzzer_type)
            fuzz_sync_dir = bane_vars.get("fuzz_sync_dir") or os.path.join(
                args.suite, "out"
            )
            action = "move-uniq"
            if args.action == "import-from":
                action = "copy-uniq"
                src_masks = [os.path.join(storage, "*")]
                fuzz_in_dir = bane_vars.get("fuzz_in_dir") or fuzzer_info.input_dir(
                    fuzz_sync_dir
                )
                dst = fuzz_in_dir
            else:  # export-to
                sync_dir_mask = fuzzer_info.sample_mask(fuzz_sync_dir, "*")
                src_masks = [sync_dir_mask]
                dst = storage

        except (FuzzDataError, BuildDetectionError, TypeError) as e:
            log.error("Wasn't able to load fuzz data suite %s: %s", args.suite, e)
            return 1
    else:
        try:
            app = args.program[0]
            run_args = args.program[1:]
        except IndexError:
            app = None
            run_args = None

        fuzzer_type = args.fuzzer_type
        dst = args.output
        src_masks = args.input
        action = args.action
        tmpdir_prefix = os.getcwd()

    if (args.run_mode == "manual" and action == "minimize") or args.run_mode == "suite":
        if fuzzer_type == "AFL++":
            minimizing_tool = "afl-cmin"
        else:
            log.warning("tool based minimization is currently only supported for AFL++")

    log.info(
        "[*] BugBane corpus tool. Selected action: %s. Source: %s, destination: %s",
        args.action,
        ", ".join(src_masks),
        dst,
    )

    tmpdir = tempfile.mkdtemp(dir=tmpdir_prefix, prefix="dedup_")

    if action.startswith("move"):
        file_action = MinimizerFileAction.MOVE
    else:
        file_action = MinimizerFileAction.COPY

    count = deduplicate_by_hashes(src_masks, tmpdir, file_action)

    log.info(
        "First stage deduplication: got %s samples",
        str(count) if count is not None else "unknown number of",
    )

    if app is not None and minimizing_tool is not None:
        log.info("[*] Build used for tool-based corpus minimization: %s", app)
        tmpdir_tool = tempfile.mkdtemp(dir=tmpdir_prefix, prefix="dedup_tool_")
        try:
            count = deduplicate_by_tool(  # TODO: respect run_env from bane_vars file
                [os.path.join(tmpdir, "*")], tmpdir_tool, minimizing_tool, app, run_args
            )
        except MinimizerError as e:
            log.error(
                "Wasn't able to minimize samples with tool %s: %s", minimizing_tool, e
            )
            return 1

        log.info(
            "Second stage deduplication with tool %s complete",
            minimizing_tool,
        )
        log.verbose2("Removing temporary directory %s", tmpdir)
        shutil.rmtree(tmpdir, ignore_errors=True)

        tmpdir = tmpdir_tool

    if not os.path.exists(dst):
        log.verbose1("Creating destination directory %s", dst)
        os.makedirs(dst)

    log.verbose1("Sychronizing samples from directory %s to %s", tmpdir, dst)
    num_copied = sync_files_by_names(src_dir=tmpdir, dst_dir=dst)
    log.info("Added %d samples to %s", num_copied, dst)

    log.verbose2("Removing temporary directory %s", tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)

    log.info("[+] Deduplication complete")

    return 0
