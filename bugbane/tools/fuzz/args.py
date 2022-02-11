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
    exit_on_bad_args(args)
    return args


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description="%(prog)s - tool to perform FUZZ testing",
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
        "--suite",
        help="input fuzzing directory",
        metavar="DIR",
        required=True,
    )
    input_group.add_argument(
        "--max-cpus",
        help="upper limit for number of CPU cores to utilize (default: 16)",
        type=int,
        default=16,
    )

    return parser


def exit_on_bad_args(args: Namespace):

    if not os.path.isdir(args.suite):
        sys.exit(f"ERROR in --suite: directory '{args.suite}' doesn't exist")
