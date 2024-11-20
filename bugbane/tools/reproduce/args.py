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

from typing import Sequence, NoReturn, Union, List

import os
import sys
import shutil
import argparse

from bugbane.version import name_version_description


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=name_version_description(
            "%(prog)s", "a tool to reproduce bugs and collect fuzz stats"
        ),
        add_help=False,
    )

    parser.add_argument(
        "-h",
        "--help",
        help="show this help message and exit; use -hh for examples",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="print more informational messages (specify up to 5 times)",
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
        "-R",
        "--hang-reproduce-limit",
        help="reproduce at most R hangs per one fuzzer instance (default: 3)",
        type=int,
        metavar="R",
        default=3,
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
    app_options.add_argument(
        "--max-file-name-len",
        help="when saving bug samples, limit the length of file names to LEN (default: 255)",
        type=int,
        metavar="LEN",
        default=255,
    )

    additional_bug_samples_options = parser.add_argument_group(
        "additional bug samples options (see -hh)"
    )
    additional_bug_samples_options.add_argument(
        "--old-bugs",
        help="a mask matching previously saved bug samples to reproduce again (regression testing)",
        metavar='"FILEMASK"',
        default=None,
    )
    additional_bug_samples_options.add_argument(
        "--saved-results-file-path",
        help="a relative path to results file appended to the value of --old-bugs (default: ../../bb_results.json)",
        metavar="RELATIVE_RESULTS_FILE_PATH",
        default="../../bb_results.json",
    )
    additional_bug_samples_options.add_argument(
        "--extra-bugs",
        help="a mask matching additional new bug samples to reproduce (foreign to BugBane-controlled fuzzer)",
        metavar='"FILEMASK"',
        default=None,
    )
    additional_bug_samples_options.add_argument(
        "--no-own-bugs",
        help="do not try to reproduce bugs in own sync directory (e.g. when fuzzers didn't ran yet; use with --old-bugs and/or --extra-bugs)",
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
        "--results-file",
        help="save json results to specified FILE (note: file is not appended)",
        metavar="FILE",
        required=True,
    )
    parser_manual.add_argument(
        "-B",
        "--bug-samples-dir",
        help="save bug samples to specified DIR (appended, created if doesn't exist)",
        metavar="DIR",
        required=True,
    )

    bindings_group = parser_manual.add_argument_group("fuzzer and tested app bindings")
    bindings_group.add_argument(
        "--spec",
        help="fuzzer type <-> sync dir and tested binary <-> results subdir binding(s)",
        nargs="+",
        action="append",
        metavar="fuzzer_type:sync_dir path/to/bin:subdir [path/to/bin:subdir ...]",
        default=None,
    )

    run_group = parser_manual.add_argument_group("tested app run options")
    run_group.add_argument(
        "program",
        metavar="[--] path/to/app [arg [...]]",
        help="tested application with its arguments, @@ gets replaced with testcase file",
        nargs=argparse.REMAINDER,
        default=None,
    )

    if len(argv) < 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)

    if args.help > 0:
        parser.print_help()
        if args.help > 1:
            # fmt: off

            print()
            print("EXPLANATION")
            print("There are 3 kinds of bug samples bugbane can use to reproduce issues:")
            print("NEW - newfound bugs, just discovered by a bugbane-controlled fuzzer (during current fuzzing campaign); reproduced using matching builds")
            print("OLD - bugs, previously discovered by bugbane-controlled fuzzer (to be used for regression testing); reproduced using matching builds")
            print("EXTRA - any additional bugs to reproduce, i.e. found by some other (not controlled by bugbane) fuzzer; reproduced using each build for each sample")
            print()

            print("EXAMPLES")
            examples = (
                ("suite .", "Only reproduce NEW bugs residing in bugbane-controlled fuzzer's sync dir"),
                ('--old-bugs "$FUZZ_TARGET/*/bug_samples/*" suite .', "Reproduce NEW and OLD bugs"),
                ('--extra-bugs "some_alien_fuzzer_dir/crashes/*" suite .', "Reproduce NEW and EXTRA bugs"),
                ('--old-bugs "$FUZZ_TARGET/*/bug_samples/*" --no-own-bugs suite .', "Only reproduce OLD bugs (i.e. prior to fuzzing for early bail)"),
                ('--extra-bugs "some_alien_fuzzer_dir/crashes/*" --no-own-bugs suite .', "Only reproduce EXTRA bugs, discovered by a fuzzer not controlled by bugbane"),
                ('--old-bugs "$FUZZ_TARGET/*/bug_samples/*" --extra-bugs "some_alien_fuzzer_dir/crashes/*" suite .', "Reproduce OLD, NEW, and EXTRA bugs"),
                ('--old-bugs "$FUZZ_TARGET/*/bug_samples/*" --extra-bugs "some_alien_fuzzer_dir/crashes/*" --no-own-bugs suite .', "Reproduce both OLD and EXTRA bugs, but not NEW bugs"),
            )
            # fmt: on

            # TODO: maybe add examples for manual mode

            for cmd, explanation in examples:
                print(f"{explanation}:")
                print(" $ bb-reproduce", cmd)
                print()

            print(
                "Note: manual mode works as well, but requires --spec or at least program with run args"
            )

        sys.exit(0)

    return args


def exit_on_bad_args(args: argparse.Namespace) -> Union[None, NoReturn]:
    if args.num_reruns <= 0:
        print(
            f"NOTE in --num-reruns: corrected value from {args.num_reruns} to 1",
            file=sys.stderr,
        )
        args.num_reruns = 1

    if args.hang_timeout <= 0:
        print(
            f"NOTE in --hang-timeout: corrected value from {args.hang_timeout} to 1",
            file=sys.stderr,
        )
        args.hang_timeout = 1

    reproduce_additional_bugs = bool(args.extra_bugs) or bool(args.old_bugs)

    if args.run_mode == "suite":
        if args.no_own_bugs and not reproduce_additional_bugs:
            sys.exit(
                "ERROR in --no-own-bugs: nothing to do! Missing --old-bugs/--extra-bugs?"
            )
        return

    # manual mode checks

    if args.program and args.program[0] == "--":
        del args.program[0]

    if args.no_own_bugs:
        print(
            "NOTE: --no-own-bugs is useless in manual mode (ignored)",
            file=sys.stderr,
        )

    # in manual mode user has to provide --spec or tested program and its run args
    if args.spec is None:
        if not args.program and args.extra_bugs is not None:
            # user asked to check bugs in custom dir (--extra-bugs),
            # but did not provide spec or prog's cmdline
            sys.exit(
                "ERROR in --extra-bugs: no --spec or program's cmdline provided in manual run mode"
                " (can't determine builds to use for --extra-bugs)"
            )

    # TODO: move specs checking to harvester class
    if args.spec is not None:
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

            build_specs: List[str] = fuzzer_dir_and_builds[1:]

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

                sync_path: str = os.path.join(syncdir, path)
                if not os.path.isdir(sync_path):
                    msg = f"ERROR in --spec {spec_name}: directory '{sync_path}' not found"
                    if not os.path.isabs(sync_path):
                        msg += f"\nNOTE: the full path checked was '{os.path.abspath(sync_path)}'"
                    sys.exit(msg)

                if args.verbose:
                    print(f"\t{app} <-> {sync_path}")

            if args.verbose:
                print()

    if not args.program:
        sys.exit(
            "ERROR: no program with its run args specified. Last arguments to the tool are expected to be in this form: -- ./some_app --some-arg @@"
        )

    t_len = len(args.program)
    if t_len < 1:
        sys.exit(
            "ERROR in program run options: you didn't specify program you want to run"
        )
