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


@FuzzerCmdFactory.register("go-fuzz")
class GoFuzzCmd(LibFuzzerCmd):
    def __init__(self):
        super().__init__()
        self.count = None
        self.output_corpus = None

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
        if run_args:
            log.warning("`run_args` are not used by go-fuzz, ignored")

        self.count = count
        self.output_corpus = output_corpus

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

        # generate command like this:
        # go-fuzz -bin=fuzz.zip -dumpcover -workdir=out 2>&1 | tee go-fuzz.log
        cmd = ""
        env_str = make_env_shell_str(run_env)
        if env_str:
            cmd += f"env {env_str} "
        cmd += "go-fuzz -bin=$appname -dumpcover "  # dump coverage profile data while fuzzing
        run_dir = os.path.dirname(output_corpus)
        log_path = os.path.join(run_dir, "go-fuzz.log")
        cmd += f"-workdir={output_corpus} 2>&1 | tee {log_path}"
        return cmd

    def make_replacements(
        self,
        cmds: List[str],
        builds: Dict[BuildType, str],
        dict_path: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Dict[str, List[str]]]:
        if dict_path:
            log.warning("dictionaries are not supported by go-fuzz, ignored")

        specs = {}

        base_cmd = cmds[0]
        del cmds[0]

        if BuildType.GOFUZZ not in builds:
            raise FuzzerCmdError("no GOFUZZ build provided")

        cmd = base_cmd.replace("$appname ", f"$appname -procs={self.count} ", 1)

        cmd = self.add_timeout_to_cmd(cmd, timeout_ms)

        cmd_with_basic_build = cmd.replace("$appname", builds[BuildType.GOFUZZ])
        cmds.append(cmd_with_basic_build)

        specs[builds[BuildType.GOFUZZ]] = [self.output_corpus]
        specs = {"go-fuzz": specs}
        return specs
