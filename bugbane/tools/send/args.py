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

from .dd_api.factory import DefectDojoAPIFactory


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="%(prog)s - tool to send issue cards to Defect Dojo",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="print more informational messages",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-i",
        "--results-file",
        help="load json results from specified FILE",
        metavar="FILE",
        default=None,
        required=True,
    )
    parser.add_argument(
        "--tsp",
        "--translate-sample-paths",
        help="sample path replacement(s) (use if paths in json differ from actual sample paths)",
        metavar="/old/path->/new/path",
        nargs="+",
        default=None,
        dest="translate_sample_paths",
    )

    dd_group = parser.add_argument_group("Defect Dojo options")
    dd_group.add_argument(
        "--api-type",
        help="API type (default: official)",
        default="official",
        choices=DefectDojoAPIFactory.registry,
    )
    dd_group.add_argument(
        "--host",
        help="url of Defect Dojo with port (example: http://10.0.0.10:8080)",
        required=True,
    )
    dd_group.add_argument(
        "--no-ssl",
        help="don't care about SSL certificate existence and validity",
        action="store_true",
    )
    dd_group.add_argument(
        "--user-name",
        help="user name (default: admin)",
        default="admin",
    )
    dd_group.add_argument(
        "--token",
        help="authorization token for user specified in --user-name",
        required=True,
    )
    dd_group.add_argument(
        "--password",
        help="user password (for web-based api only)",
        default=None,
    )
    dd_group.add_argument("--user-id", help="user id (default: 1)", default=1, type=int)
    dd_group.add_argument(
        "--engagement",
        help="engagement id",
        type=int,
        required=True,
    )
    dd_group.add_argument(
        "--test-type",
        help="id of test type created in Defect Dojo",
        required=True,
        type=int,
    )

    if len(argv) < 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)

    exit_on_bad_args(args)

    return args


def exit_on_bad_args(args):

    if args.user_id < 1:
        sys.exit("ERROR in --user-id: bad user id '%d'" % args.user_id)

    if args.engagement < 1:
        sys.exit("ERROR in --engagement: bad engagement id '%d'" % args.engagement)

    if not os.path.isfile(args.results_file):
        sys.exit("ERROR in --results-file: file '%s' doesn't exist" % args.results_file)

    if os.path.getsize(args.results_file) == 0:
        sys.exit("ERROR in --results-file: file '%s' is empty" % args.results_file)
