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
        description="%(prog)s - tool to create builds for fuzzing",
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
        help="assume DIR is directory with sources, bugbane.json and build.sh",
        metavar="DIR",
        required=True,
    )

    output_group = parser.add_argument_group("output options")
    output_group.add_argument(
        "-o",
        "--output",
        help="save build results to DIR",
        metavar="DIR",
        default="fuzz_builds",
    )

    return parser


def exit_on_bad_args(args: Namespace):

    if not os.path.isdir(args.input):
        sys.exit(f"ERROR in --input: directory '{args.input}' doesn't exist")


def post_process_args(args: Namespace):
    ...
