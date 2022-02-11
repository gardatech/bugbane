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
import argparse


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="%(prog)s - tool to collect fuzzing results and prepare results file",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="print more informational messages",
        action="count",
        default=0,
    )
    app_options = parser.add_argument_group("application options")
    app_options.add_argument(
        "-H",
        "--hang-timeout",
        help="consider application hang if it runs for longer than N milliseconds (default: 5000)",
        type=int,
        metavar="N",
        default=5000,
    )
    app_options.add_argument(
        "--num-reruns",
        help="make at most N runs on same sample if application doesn't crash/hang right away (default: 3)",
        type=int,
        metavar="N",
        default=3,
    )
    app_options.add_argument(
        "--abspath",
        help="use absolute paths for tested binaries and testcase files while reproducing",
        action="store_true",
    )

    supbarsers = parser.add_subparsers(help="run mode", dest="run_mode")

    parser_suite = supbarsers.add_parser("suite", help="fuzz suite run mode")
    parser_suite.add_argument(
        "suite",
        help="path to fuzz suite with tested application builds and configuration file",
    )

    parser_manual = supbarsers.add_parser("manual", help="manual run mode")
    parser_manual.add_argument(
        "--src-path",
        help="path to sources used to build application (for better location detection, directory may not exist)",
        default=None,
        metavar="PATH",
    )
    parser_manual.add_argument(
        "-o",
        "--output",
        help="save json results to specified FILE (note: file is not appended)",
        metavar="FILE",
        required=True,
    )

    bindings_group = parser_manual.add_argument_group("fuzzer and tested app bindings")
    bindings_group.add_argument(
        "--spec",
        help="fuzzer type <-> sync dir and tested binary <-> results subdir binding(s)",
        nargs="+",
        action="append",
        metavar="fuzzer_type:sync_dir path/to/bin:subdir [path/to/bin:subdir ...]",
        required=True,
    )

    run_group = parser_manual.add_argument_group("tested app run options")
    run_group.add_argument(
        "program",
        metavar="[--] path/to/app [arg [...]]",
        help="tested application with its arguments, @@ gets replaced with testcase file",
        nargs=argparse.REMAINDER,
    )

    if len(argv) < 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)

    return args


def exit_on_bad_args(args):

    if args.num_reruns <= 0:
        if args.verbose:
            print(
                f"NOTE in --num-reruns: corrected value from {args.num_reruns} to 1",
                file=sys.stderr,
            )
        args.num_reruns = 1

    if args.hang_timeout <= 0:
        if args.verbose:
            print(
                f"NOTE in --hang-timeout: corrected value from {args.hang_timeout} to 1",
                file=sys.stderr,
            )
        args.hang_timeout = 1

    if args.run_mode == "suite":
        return

    for fuzzer_dir_and_builds in args.spec:

        if len(fuzzer_dir_and_builds) < 2:
            sys.exit(
                f"ERROR in --spec {fuzzer_dir_and_builds}: at least two values required"
            )

        spec_name = "'" + " ".join(fuzzer_dir_and_builds) + "'"

        fuzzer_and_syncdir = fuzzer_dir_and_builds[0]
        if ":" not in fuzzer_and_syncdir:
            sys.exit(
                f"ERROR in --spec {spec_name}: missing fuzzer_type and sync dir separator ':'"
            )

        fuzzer_type, syncdir = fuzzer_and_syncdir.split(":", 1)

        build_specs = fuzzer_dir_and_builds[1:]

        if args.verbose:
            print(f"Have the following spec: {spec_name}")
            print(f"Checking builds for fuzzer type '{fuzzer_type}'... ")

        for app_and_dir in build_specs:
            if ":" not in app_and_dir:
                sys.exit(
                    f"ERROR in --spec {spec_name}: missing app and result dir separator ':' for app '{app_and_dir}'"
                )

            app, path = app_and_dir.split(":", 1)
            if shutil.which(app) is None:
                sys.exit(f"ERROR in --spec {spec_name}: binary '{app}' not found")

            sync_path = os.path.join(syncdir, path)
            if not os.path.isdir(sync_path):
                msg = f"ERROR in --spec {spec_name}: directory '{sync_path}' not found"
                if not os.path.isabs(sync_path):
                    msg += f"\nNOTE: the full path checked was '{os.path.abspath(sync_path)}'"
                sys.exit(msg)

            if args.verbose:
                print(f"\t{app} <-> {sync_path}")

        if args.verbose:
            print()

    t_len = len(args.program)
    if t_len < 1 or (args.program[0] == "--" and t_len < 2):
        sys.exit(
            "ERROR in program run options: you didn't specify program you want to run"
        )

    if args.program[0] == "--":
        del args.program[0]
