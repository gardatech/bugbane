# Copyright 2022-2024 Garda Technologies, LLC. All rights reserved.
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

from bugbane.modules.log import get_verbose_logger
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
    log = get_verbose_logger(__name__, args.verbose)

    minimizing_tool = None

    if args.run_mode == "suite":
        try:
            _, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.suite)
            tested_binary_path = bane_vars.get("tested_binary_path")

            if not tested_binary_path:
                raise FuzzDataError("no tested_binary_path in configuration")

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
            run_env = bane_vars.get("run_env") or {}
            fuzzer_type = bane_vars.get("fuzzer_type")
            if not fuzzer_type:
                raise FuzzDataError("no fuzzer_type in configuration")

            prog_timeout = bane_vars.get("timeout")

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

        run_env = {}

        fuzzer_type = args.fuzzer_type
        prog_timeout = args.timeout
        dst = args.output
        src_masks = args.input
        action = args.action
        tmpdir_prefix = os.getcwd()

    if (args.run_mode == "manual" and action == "minimize") or args.run_mode == "suite":
        fuzzer_to_cmin_map = {
            "AFL++": "afl-cmin",
            "libFuzzer": "libFuzzer",
        }
        minimizing_tool = fuzzer_to_cmin_map.get(fuzzer_type)
        if minimizing_tool is None:
            log.warning(
                "tool based minimization is currently only supported for the following fuzzers: %s",
                ", ".join(fuzzer_to_cmin_map),
            )

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
            masks = [os.path.join(tmpdir, "*")]
            count = deduplicate_by_tool(
                masks=masks,
                dest=tmpdir_tool,
                tool_name=minimizing_tool,
                program=app,
                run_args=run_args,
                run_env=run_env,
                prog_timeout_ms=prog_timeout,
                tool_timeout_sec=args.tool_timeout,
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
        log.verbose2("Removing temporary directory '%s'", tmpdir)
        shutil.rmtree(tmpdir, ignore_errors=True)

        tmpdir = tmpdir_tool

    if not os.path.exists(dst):
        log.verbose1("Creating destination directory '%s'", dst)
        os.makedirs(dst)

    log.verbose1("Sychronizing samples from directory '%s' to '%s'", tmpdir, dst)
    num_copied = sync_files_by_names(
        src_dir=tmpdir, dst_dir=dst, max_sample_size=args.max_sample_size
    )
    log.info("Added %d samples to '%s'", num_copied, dst)

    log.verbose2("Removing temporary directory '%s'", tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)

    log.info("[+] Deduplication complete")

    return 0
