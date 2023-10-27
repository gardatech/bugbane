# Copyright 2022-2023 Garda Technologies, LLC. All rights reserved.
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
import pprint
from argparse import Namespace

from bugbane.modules.log import get_verbose_logger, Logger
from bugbane.modules.credentials import (
    Credentials,
    EmptyLoginException,
    NoSecretDefinedException,
)

from .args import parse_args

from .dd_api.abc import DefectDojoAPI, DefectDojoAPIError
from .dd_api.factory import DefectDojoAPIFactory
from .defectdojo_sender import DefectDojoSender


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_verbose_logger(__name__, args.verbose)

    log.info("[*] BugBane send tool")

    try:
        dd_api = create_dd_api_from_args(args, log)
    except CreateAPIException as e:
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

    bug_samples_dir = "bug_samples"
    if os.path.isdir(bug_samples_dir):
        os.chdir(bug_samples_dir)

    log.info("Fuzz statistics:")
    log.info(pprint.pformat(sender.fuzz_stats, indent=4))

    sender.create_dd_findings()

    return 0


class CreateAPIException(Exception):
    """Exception: wasn't able to create DD API instance."""


def create_dd_api_from_args(args: Namespace, log: Logger) -> DefectDojoAPI:
    """
    args: result of ArgumentParser.parse_args()
    Create DefectDojo api object using DefectDojoAPIFactory.
    Instantiate api object based on args and return it.
    """

    verify_ssl = not args.no_ssl
    debug = args.verbose > 4

    try:
        api: DefectDojoAPI = DefectDojoAPIFactory.create(args.api_type)
        creds = get_dojo_creds(args, log)
        api.instantiate_api(
            host=args.host,
            verify_ssl=verify_ssl,
            user_name=creds.login,  # pyright: ignore (empty login gets fixed in get_dojo_creds)
            user_id=args.user_id,
            user_token=creds.secret,
            engagement_id=args.engagement,
            test_type_id=args.test_type,
            debug=debug,
        )
        return api
    except (DefectDojoAPIError, TypeError) as e:
        raise CreateAPIException(f"API creation error: {e}") from e


def get_dojo_creds(args: Namespace, log: Logger) -> Credentials:
    dojo_creds_name = "DEFECT_DOJO"
    try:
        creds = Credentials.from_env(dojo_creds_name)
        if creds.login is None:
            creds.login = args.user_name
            log.info("using Defect Dojo creds: user from --user-name, token from env")
        else:
            log.info("using Defect Dojo creds from env")

        if args.token is not None:
            log.warning(
                "the argument --token is ignored, as Defect Dojo token was already defined in env variables. Please remove the argument",
            )
        return creds

    except EmptyLoginException as e:
        raise CreateAPIException("empty login was specified in env variables") from e

    except NoSecretDefinedException:
        log.warning(
            "using Defect Dojo credentials from cmdline arguments, consider using env variables: BB_%s_LOGIN, BB_%s_SECRET",
            dojo_creds_name,
            dojo_creds_name,
        )
        return Credentials(login=args.user_name, secret=args.token)
