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
Tool to collect coverage
"""

import os
import sys
import shlex

from bugbane.modules.log import get_verbose_logger
from bugbane.modules.fuzz_data_suite import FuzzDataError, FuzzDataSuite
from bugbane.modules.builds import BuildDetectionError, detect_builds

from bugbane.modules.stats.coverage.coverage_stats import (
    CoverageStats,
    CoverageStatsError,
)
from bugbane.modules.stats.coverage.factory import CoverageStatsFactory

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo


from .collector.collector import CoverageCollector, CoverageCollectorError
from .collector.factory import CoverageCollectorFactory

from .args import parse_args


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_verbose_logger(__name__, args.verbose)

    log.info("[*] BugBane coverage tool")

    if args.run_mode == "suite":
        try:
            _, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.suite)
            tested_binary_path = bane_vars.get("tested_binary_path") or None

            builds = detect_builds(args.suite, tested_binary_path)

            coverage_build_path = next(
                (path for btype, path in builds.items() if btype.is_coverage()), None
            )
            if not coverage_build_path:
                raise BuildDetectionError("coverage build not found")

            run_args = shlex.split(bane_vars.get("run_args") or "")
            run_env = bane_vars.get("run_env") or {}
            coverage_type = bane_vars.get("coverage_type")
            fuzzer_type = bane_vars.get("fuzzer_type")
            coverage_report_path = os.path.join(args.suite, "coverage_report")

            # TODO: use out_uniq after minimizing output corpus
            fuzz_sync_dir = bane_vars.get("fuzz_sync_dir") or os.path.join(
                args.suite, "out"
            )

            fuzzer_info: FuzzerInfo = FuzzerInfoFactory.create(fuzzer_type)
            sample_masks = [fuzzer_info.sample_mask(fuzz_sync_dir, "*1")]
            run_args = fuzzer_info.one_sample_run_args(run_args)

            src_root = bane_vars.get("src_root")
            if not src_root:
                raise FuzzDataError("no src_root in configuration file")

            # if fuzzer doesn't collect coverage, then
            # coverage data is expected at src_root
            cov_files_path = fuzzer_info.coverage_dir(fuzz_sync_dir) or src_root

        except (FuzzDataError, BuildDetectionError) as e:
            log.error("Wasn't able to load fuzz data suite %s: %s", args.suite, e)
            return 1
    else:
        coverage_build_path = args.program[0]
        run_args = args.program[1:]
        run_env = {}
        coverage_type = args.cov_type
        coverage_report_path = args.output
        src_root = args.src_root
        cov_files_path = args.cov_files_path
        sample_masks = args.masks

    cov_collector: CoverageCollector = CoverageCollectorFactory.create(coverage_type)
    log.verbose1("Using %s", cov_collector.__class__.__name__)

    cov_collector.assign_application(
        binary=coverage_build_path, run_args=run_args, run_env=run_env
    )
    cov_collector.assign_src_root(src_root)
    cov_collector.assign_cov_files_path(cov_files_path)
    cov_collector.assign_sample_masks(sample_masks)

    log.info("Will collect coverage data at %s", cov_files_path)

    try:
        cov_collector.collect()

        log.info("Generating coverage report")
        cov_collector.generate_report(
            coverage_report_path, include_source=not args.exclude_source_code
        )
    except CoverageCollectorError as e:
        log.error("Wasn't able to create coverage report: %s", e)
        return 1

    log.verbose2("Getting coverage percents...")
    try:
        cov_stats: CoverageStats = CoverageStatsFactory.create(coverage_type)
        log.verbose1("Using %s coverage stats", cov_stats.__class__.__name__)
        cov_stats.load(coverage_report_path)
        log.info(cov_stats)
    except CoverageStatsError as e:
        log.error("Error while loading coverage stats: %s", e)
        return 1

    log.info("Coverage results saved to %s", coverage_report_path)
    log.info("[+] Coverage collection complete")  # , updating configuration file")

    return 0
