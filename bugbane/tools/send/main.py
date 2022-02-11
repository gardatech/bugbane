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
import pprint
from argparse import Namespace

from bugbane.modules.log import get_first_logger

from .args import parse_args

from .dd_api.abc import DefectDojoAPI, DefectDojoAPIError
from .dd_api.factory import DefectDojoAPIFactory
from .defectdojo_sender import DefectDojoSender


def create_dd_api_from_args(args: Namespace) -> DefectDojoAPI:
    """
    args: result of ArgumentParser.parse_args()
    Create DefectDojo api object using DefectDojoAPIFactory.
    Instantiate api object based on args and return it.
    """

    api = DefectDojoAPIFactory.create(args.api_type)
    verify_ssl = not args.no_ssl
    debug = args.verbose > 4
    api.instantiate_api(
        host=args.host,
        verify_ssl=verify_ssl,
        user_name=args.user_name,
        user_id=args.user_id,
        user_token=args.token,
        user_password=args.password,
        engagement_id=args.engagement,
        test_type_id=args.test_type,
        debug=debug,
    )
    return api


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_first_logger(__name__, args.verbose)

    try:
        dd_api = create_dd_api_from_args(args)
    except (DefectDojoAPIError, TypeError) as e:
        log.error("during creation of DefectDojoAPI object: %s", e)
        return 1

    log.info(
        "using %s as API for communication with %s",
        dd_api.__class__.__name__,
        args.host,
    )

    sender = DefectDojoSender(dd_api, args.translate_sample_paths, args.results_file)

    try:
        sender.load_cards()
    except DefectDojoAPIError as e:
        log.error("during loading of issue cards. Message: %s", e)
        return 1

    log.info("Fuzz statistics:")
    log.info(pprint.pformat(sender.fuzz_stats, indent=4))

    sender.create_dd_findings()

    return 0
