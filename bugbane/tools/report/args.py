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
import argparse
from argparse import Namespace

from bugbane.modules.file_utils import none_on_bad_nonempty_file
from bugbane.modules.stats.coverage.factory import CoverageStatsFactory
from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory

from .emitters.factory import EmitterFactory


def parse_args(argv):
    parser = create_argument_parser()

    if len(argv) < 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)
    post_process_args(args)
    exit_on_bad_args(args)
    return args


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description="%(prog)s - tool to generate fuzzing reports",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="print more informational messages (specify up to 5 times)",
        action="count",
        default=0,
    )

    default_templates_path = os.path.join(os.path.dirname(__file__), "templates")
    template_group = parser.add_argument_group("template options")
    template_group.add_argument(
        "--templates",
        help=f"look for jinja2 templates in DIR directory (default: {default_templates_path})",
        metavar="DIR",
        default=default_templates_path,
    )
    template_group.add_argument(
        "--template-name",
        help="use this template as base (default: report.{format})",
        default=None,
    )

    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "-f",
        "--format",
        help="output report format (default: md)",
        choices=EmitterFactory.registry,
        default="md",
    )
    output_group.add_argument(
        "--name",
        help="report file name (without extension)",
        default=None,
        required=True,
    )

    screenshot_group = parser.add_argument_group("screenshot options")
    screenshot_group.add_argument(
        "--dump-screener",
        help="screenshot utility to use for screen dumps (default: pango)",
        choices=["pango"],
        default="pango",
    )
    screenshot_group.add_argument(
        "--html-screener",
        help="screenshot utility to use for html (default: weasyprint)",
        choices=["weasyprint", "selenium"],
        default="weasyprint",
    )

    supbarsers = parser.add_subparsers(help="run mode", dest="run_mode")

    parser_suite = supbarsers.add_parser("suite", help="fuzz suite run mode")
    parser_suite.add_argument(
        "suite",
        help="path to fuzz suite containing all the fuzzing results",
    )

    parser_manual = supbarsers.add_parser("manual", help="manual run mode")
    parser_manual.add_argument(
        "-i",
        "--suite",
        help="load fuzzing results from DIR directory",
        metavar="DIR",
        required=True,
    )
    parser_manual.add_argument(
        "--cov-type",
        help="format of code coverage report in fuzzing results",
        choices=CoverageStatsFactory.registry,
        required=True,
    )
    parser_manual.add_argument(
        "--fuzzer-type",
        help="format of fuzzer stats in fuzzing results",
        choices=FuzzStatsFactory.registry,
        required=True,
    )
    parser_manual.add_argument(
        "-o",
        "--output",
        help="save report to specified DIR (default: current dir)",
        metavar="DIR",
        default=".",
    )

    return parser


def exit_on_bad_args(args: Namespace):

    if not os.path.isdir(args.suite):
        sys.exit(f"ERROR: suite directory '{args.suite}' doesn't exist")

    if not os.path.isdir(args.templates):
        sys.exit(f"ERROR in --templates: directory '{args.templates}' doesn't exist")

    template_path = os.path.join(args.templates, args.template_name)
    checked_path = none_on_bad_nonempty_file(template_path)
    if not checked_path:
        sys.exit(
            f"ERROR in --templates/--template-name: file '{template_path}' doesn't exist, empty or not accessible"
        )


def post_process_args(args: Namespace):

    if args.template_name is None:
        args.template_name = f"report.{args.format}"
