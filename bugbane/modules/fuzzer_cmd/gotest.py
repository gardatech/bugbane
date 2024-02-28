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

from typing import List, Dict, Tuple, Optional

import os
from bugbane.modules.log import getLogger

from bugbane.modules.string_utils import replace_part_in_str_list

log = getLogger(__name__)


from bugbane.modules.build_type import BuildType
from bugbane.modules.process import make_env_shell_str

from .libfuzzer import LibFuzzerCmd
from .fuzzer_cmd import FuzzerCmdError
from .factory import FuzzerCmdFactory


@FuzzerCmdFactory.register("go-test")
class GoTestCmd(LibFuzzerCmd):
    """
    Command generator for native Go fuzzer (`go test . -fuzz=...`).
    Relies on the fact that tested app was already built with a command like this:
    ```
    go test . -fuzz=FuzzSomething -o fuzz -c -cover
    ```
    NOTE: even if there are multiple FuzzXxx functions available,
    only one needs to be passed in the -fuzz option (any one) and the resulting binary
    will still contain all available functions.

    This generator is then creates a command like this:
    ```
    ./fuzz \
        -test.fuzz=FuzzParse \
        -test.parallel=6 \
        -test.fuzztime=1440s \
        -test.fuzzcachedir=out \
        -test.coverprofile=out/coverprofile \
        2>&1 \
        | tee go-test-fuzz.log
    ```
    NOTE: -test.fuzz option will be added only if provided in `run_args`
    bugbane variable.
    NOTE: crashes/hangs will always be saved in "testdata" directory and there's
    no way to control it in `go test`.
    """

    def __init__(self):
        super().__init__()
        self.run_args = ""

    def generate(
        self,
        run_args: str,
        run_env: Dict[str, str],
        input_corpus: str,
        output_corpus: str,
        count: int,
        builds: Dict[BuildType, str],
        dict_path: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> Tuple[List[str], Dict[str, Dict[str, List[str]]]]:
        self.count = count
        self.output_corpus = output_corpus
        self.run_args = run_args

        cmds = [self.generate_one(input_corpus, output_corpus, run_env)]
        specs = self.make_replacements(cmds, builds, dict_path, timeout_ms)

        replace_part_in_str_list(  # replace $i with 1-based indexes
            cmds,
            "$i",
            "$i",
            -1,
            0,
            len(cmds) - 1,
        )

        return (cmds, specs)

    def generate_one(
        self, input_corpus: str, output_corpus: str, run_env: Dict[str, str]
    ) -> str:
        cmd = ""
        env_str = make_env_shell_str(run_env)
        if env_str:
            cmd += f"env {env_str} "

        cmd += "$appname"
        run_args = self.run_args or ""
        if "-test.fuzz=Fuzz" not in run_args:
            raise FuzzerCmdError(
                'empty or bad "run_args" option provided.'
                " Please specify -test.fuzz option, e.g. -test.fuzz=FuzzParse"
            )
        cmd += f" {run_args}"  # for -test.fuzz=FuzzXxx
        cover_path = os.path.join(output_corpus, "coverprofile")
        cmd += f" -test.coverprofile={cover_path}"  # dump coverage profile data while fuzzing
        run_dir = os.path.dirname(output_corpus)
        log_path = os.path.join(run_dir, "go-test-fuzz.log")
        cmd += f' -test.fuzzcachedir={output_corpus} 2>&1 | tee "{log_path}"'
        return cmd

    def make_replacements(
        self,
        cmds: List[str],
        builds: Dict[BuildType, str],
        dict_path: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Dict[str, List[str]]]:
        if dict_path:
            log.warning("dictionaries are not supported by `go test` fuzzer, ignored")
        if timeout_ms:
            log.warning(
                "timeout specified but ignored, because `go test`"
                " fuzzer treats fuzz timeouts as errors"
            )

        specs = {}

        base_cmd = cmds[0]
        del cmds[0]

        if BuildType.GOTEST not in builds:
            raise FuzzerCmdError("no GOTEST build provided")

        cmd = base_cmd.replace("$appname ", f"$appname -test.parallel={self.count} ", 1)

        cmd_with_basic_build = cmd.replace("$appname", builds[BuildType.GOTEST])
        cmds.append(cmd_with_basic_build)

        specs[builds[BuildType.GOTEST]] = [self.output_corpus]
        specs = {"go-test": specs}
        return specs
