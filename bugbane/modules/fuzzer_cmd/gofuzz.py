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

from typing import Optional, List, Dict, Tuple

import os
import logging

from bugbane.modules.string_utils import replace_part_in_str_list

log = logging.getLogger(__name__)


from bugbane.modules.build_type import BuildType

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
        input_corpus: str,
        output_corpus: str,
        count: int,
        builds: Dict[BuildType, str],
    ) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
        self.count = count
        self.output_corpus = output_corpus

        cmds = [self.generate_one(input_corpus, output_corpus) + " " + run_args]
        specs = self.make_replacements(cmds, builds)

        replace_part_in_str_list(  # replace $i with 1-based indexes
            cmds,
            "$i",
            "$i",
            -1,
            0,
            len(cmds) - 1,
        )

        specs = {"go-fuzz": specs}
        return (cmds, specs)

    def generate_one(self, input_corpus: str, output_corpus: str) -> str:
        cmd = "go-fuzz -bin=$appname -dumpcover "  # dump coverage profile data while fuzzing
        run_dir = os.path.dirname(output_corpus)
        log_path = os.path.join(run_dir, "go-fuzz.log")
        cmd += f"-workdir={output_corpus} 2>&1 | tee {log_path}"
        return cmd

    def make_replacements(
        self, cmds: List[str], builds: Dict[BuildType, str]
    ) -> Dict[str, Dict[str, str]]:
        specs = {}

        base_cmd = cmds[0]
        del cmds[0]

        if BuildType.GOFUZZ not in builds:
            raise FuzzerCmdError("no GOFUZZ build provided")

        cmd = base_cmd.replace(" ", f" -procs={self.count} ", 1)
        cmd_with_basic_build = cmd.replace("$appname", builds[BuildType.GOFUZZ])
        cmds.append(cmd_with_basic_build)
        specs[builds[BuildType.GOFUZZ]] = self.output_corpus

        return specs
