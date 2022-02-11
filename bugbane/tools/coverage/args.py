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

import shutil
import sys
import argparse
from argparse import Namespace

from bugbane.modules.file_utils import none_on_bad_nonempty_dir
from bugbane.modules.stats.coverage.factory import CoverageStatsFactory


def parse_args(argv):
    parser = create_argument_parser()

    if len(argv) < 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)
    exit_on_bad_args(args)
    post_process_args(args)
    return args


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description="%(prog)s - tool to collect code coverage information",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="print more informational messages (specify up to 5 times)",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-X",
        "--exclude-source-code",
        help="don't include source code in resulting report (default: code included)",
        action="store_true",
    )

    supbarsers = parser.add_subparsers(help="run mode", dest="run_mode")

    parser_suite = supbarsers.add_parser("suite", help="fuzz suite run mode")
    parser_suite.add_argument(
        "suite",
        help="path to fuzz suite with coverage build and configuration file",
    )

    parser_manual = supbarsers.add_parser("manual", help="manual run mode")
    input_group = parser_manual.add_argument_group("input options")
    input_group.add_argument(
        "--cov-type",
        help="coverage collection tools (default: lcov)",
        choices=CoverageStatsFactory.registry,
        default="lcov",
    )
    input_group.add_argument(
        "--masks",
        help="masks to find samples on disk (example: './out/*/queue/id*')",
        metavar="MASK",
        nargs="+",
        required=True,
    )

    output_group = parser_manual.add_argument_group("output options")
    output_group.add_argument(
        "-C",
        "--cov-files-path",
        help="path where intermediate coverage files will be generated when running tested application",
        metavar="DIR",
        required=True,
    )
    output_group.add_argument(
        "-S",
        "--src-root",
        help="path where tested application was built (may not exist)",
        metavar="DIR",
        required=True,
    )
    output_group.add_argument(
        "-o",
        "--output",
        help="save coverage report to directory (default: ./coverage_report)",
        metavar="DIR",
        default="./coverage_report",
    )

    program_group = parser_manual.add_argument_group("program run options")
    program_group.add_argument(
        "program",
        nargs=argparse.REMAINDER,
        metavar="...",
        help="tested program with its arguments (example: ./myapp --file @@)",
    )

    return parser


def exit_on_bad_args(args: Namespace):
    if args.run_mode == "suite":
        path = none_on_bad_nonempty_dir(args.suite)
        if path is None:
            sys.exit(
                f"ERROR: nonexistent, empty or inaccessible fuzz suite {args.suite}"
            )

        return

    if not args.program:
        sys.exit("ERROR: tested program is not specified")

    prog_len = len(args.program)
    if args.program[0] == "--":
        len_required = 2
    else:
        len_required = 1

    if prog_len < len_required:
        sys.exit("ERROR: tested program is not specified")

    binary = args.program[len_required - 1]

    if shutil.which(binary) is None:
        sys.exit("ERROR: tested program doesn't exist or isn't executable")


def post_process_args(args: Namespace):
    if args.run_mode == "suite":
        return

    if args.program[0] == "--":
        del args.program[0]
