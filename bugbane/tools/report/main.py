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

import os
import sys
import shutil

from bugbane.modules.log import get_first_logger
from bugbane.modules.fuzz_data_suite import FuzzDataSuite, FuzzDataError
from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory
from bugbane.modules.stats.coverage.factory import CoverageStatsFactory
from bugbane.modules.fuzzer_cmd.fuzzer_cmd import FuzzerCmd
from bugbane.modules.fuzzer_cmd.factory import FuzzerCmdFactory

from .args import parse_args
from .emitters.factory import EmitterFactory
from .emitters.emitter_with_screenshots import EmitterWithScreenshots
from .screenshot.factory import ScreenshotMakerFactory


def main(argv=None):
    """
    1. Load fuzzing suite from directory of special structure
    2. Create screenshots with help of ansifilter, pango-view and weasyprint
    3. Make data dictionary from fuzzing suite
    4. Render template with Jinja2 using data dictionary
    """

    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_first_logger(__name__, args.verbose)

    if args.dump_screener == "pango":
        if shutil.which("pango-view") is None:
            log.error("pango-view wasn't found in PATH")
            return 1

        if shutil.which("ansifilter") is None:
            log.warning("ansifilter wasn't found in PATH, expect bad screenshots")

    try:
        suite = FuzzDataSuite.from_fuzzing_suite_dir(args.suite)
    except FuzzDataError as e:
        log.error("Wasn't able to load fuzzing suite paths: %s", e)
        return 1
    log.verbose1("Loaded fuzzing suite: %s", suite)

    if args.run_mode == "suite":
        bane_vars = suite.load_vars()
        try:
            fuzzer_type = bane_vars["fuzzer_type"]
            cov_type = bane_vars["coverage_type"]
            output_dir = os.path.dirname(os.path.normpath(bane_vars["fuzz_sync_dir"]))
        except KeyError as e:
            log.error("Expected field %s is missing in configuration file", e)
            return 1
    else:
        fuzzer_type = args.fuzzer_type
        cov_type = args.cov_type
        output_dir = args.output

    try:
        emitter: EmitterWithScreenshots = EmitterFactory.create(args.format)
        if not isinstance(emitter, EmitterWithScreenshots):
            raise TypeError(f"bad emitter selected: {emitter.__class__.__name__}")
        log.verbose1("Using %s emitter", emitter.get_format_name())

        cov_stats = CoverageStatsFactory.create(cov_type)
        log.verbose1("Using %s coverage stats", cov_stats.__class__.__name__)

        fuzz_stats = FuzzStatsFactory.create(fuzzer_type)
        log.verbose1("Using %s fuzzer stats", fuzz_stats.__class__.__name__)

        fuzzer_cmd: FuzzerCmd = FuzzerCmdFactory.create(fuzzer_type)
        log.verbose1("Using %s fuzzer cmd", fuzzer_cmd.__class__.__name__)
    except TypeError as e:
        log.error("Wasn't able to create factory class instance: %s", e)
        return 1

    try:
        dump_screener = ScreenshotMakerFactory.create(args.dump_screener)
        log.verbose1("Using %s ansi screenshot maker", dump_screener.__class__.__name__)

        html_screener = ScreenshotMakerFactory.create(args.html_screener)
        log.verbose1("Using %s html screenshot maker", html_screener.__class__.__name__)
    except TypeError as e:
        log.error("Wasn't able to create screenshot maker: %s", e)
        return 1

    suite.set_coverage_stats(cov_stats)
    suite.set_fuzz_stats(fuzz_stats)

    emitter.assign_suite(suite)
    emitter.set_template_path(args.templates, args.template_name)

    emitter.set_ansi_screenshot_maker(dump_screener)
    emitter.set_html_screenshot_maker(html_screener)

    screenshots_out_dir = os.path.join(output_dir, "screenshots")
    fuzzer_has_stats = fuzzer_cmd.stats_cmd("check") is not None
    emitter.make_screenshots(screenshots_out_dir, fuzzer_has_stats)

    data = emitter.render()
    if output_dir == "-":
        print(data)
    else:
        output_file_path = os.path.join(
            output_dir, args.name + "." + emitter.get_report_file_extension()
        )
        with open(output_file_path, "wt", encoding="utf-8") as f:
            print(data, file=f)

    return 0
