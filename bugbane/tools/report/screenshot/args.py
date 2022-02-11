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

import sys
import argparse
from argparse import Namespace

from bugbane.modules.file_utils import none_on_bad_nonempty_file
from .factory import ScreenshotMakerFactory


def parse_args(argv):
    parser = create_argument_parser()

    if len(argv) < 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)
    exit_on_bad_args(args)
    return args


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description="%(prog)s - tool to create images from html and ansi dump files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="print more informational messages (specify up to 5 times)",
        action="count",
        default=0,
    )
    input_group = parser.add_argument_group("input options")
    input_group.add_argument(
        "-i",
        "--input",
        help="input file to convert to PNG",
        required=True,
    )

    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "-S",
        "--screener",
        help="screenshot utility to use (default: pango)",
        choices=ScreenshotMakerFactory.registry,
        default="pango",
    )
    output_group.add_argument(
        "-o",
        "--output",
        help="save output file to specified path",
        required=True,
    )
    output_group.add_argument(
        "--dpi",
        help="resulting image resolution (default: 180)",
        type=int,
        default=180,
    )

    return parser


def exit_on_bad_args(args: Namespace):
    input_file = none_on_bad_nonempty_file(args.input)
    if not input_file:
        sys.exit(
            f"ERROR in --input: file '{args.input_suite}' does not exist, empty or not readable"
        )

    if args.dpi < 1:
        sys.exit(f"ERROR in --dpi: value '{args.dpi}' is invalid")
