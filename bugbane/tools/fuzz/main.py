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

import sys
import shutil

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.fuzz_data_suite import FuzzDataSuite, FuzzDataError

from .args import parse_args

from .fuzz_config import FuzzConfig, FuzzConfigError
from .fuzz_box import FuzzBox, FuzzBoxError, CannotContinueFuzzingException


def main(argv=None):
    """
    1. Load tested app information, fuzzer_type, fuzz_cores from bane_vars file
    2. Generate fuzz & tmux commands
    3. Fuzz until stop condition reached
    4. Print stats & progress
    5. Update bane_vars file
    """

    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log.set_verbosity_level(args.verbose)

    log.info("[*] BugBane fuzz tool")

    if shutil.which("tmux") is None:
        log.error("tmux not found in PATH")
        return 1

    try:
        suite, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.suite)
        fuzz_config = FuzzConfig.from_dict(config_vars=bane_vars, suite_dir=args.suite)
    except FuzzDataError as e:
        log.error("Wasn't able to load fuzzing suite paths: %s", e)
        return 1
    except FuzzConfigError as e:
        log.error("bad configuration: %s", e)
        return 1

    log.verbose1("Loaded fuzzing suite: %s", suite)

    fuzzer = None
    interrupted = False
    try:
        fuzzer = FuzzBox(fuzz_config=fuzz_config, suite_dir=args.suite, suite=suite)
        fuzzer.start(
            start_interval_ms=args.start_interval, max_cpus_argument=args.max_cpus
        )
        fuzzer.wait_until_stop_condition()
    except CannotContinueFuzzingException as e:
        log.warning("while running fuzzers: %s", str(e))
        interrupted = True
    except FuzzBoxError as e:
        log.error("while running fuzzers: %s", str(e))
        return 1
    except KeyboardInterrupt:
        log.info("")
        log.info("[!] Fuzzing stopped by signal SIGINT")
        interrupted = True
    finally:
        if fuzzer:
            fuzzer.stop_and_update_vars(bane_vars, interrupted=interrupted)

    log.info("[+] Fuzzing complete, updating configuration file")
    suite.save_vars(bane_vars)

    return 0
