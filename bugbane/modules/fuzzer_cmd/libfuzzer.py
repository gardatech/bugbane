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

from .fuzzer_cmd import FuzzerCmd, FuzzerCmdError
from .factory import FuzzerCmdFactory


@FuzzerCmdFactory.register("libFuzzer")
class LibFuzzerCmd(FuzzerCmd):
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
        """
        Generate commands to run fuzzer on `count` cores:
            - one cmd for each kind of sanitizer builds;
            - rest of the `count` cmds use basic build if it's available (otherwise will use first available sanitizer)

        Return tuple: (cmds, reproduce_specs)
        """
        self.count = count
        self.output_corpus = output_corpus

        cmds = [self.generate_one(input_corpus, output_corpus)]
        specs = self.make_replacements(cmds, builds)

        replace_part_in_str_list(  # replace $i with 1-based indexes
            cmds,
            "$i",
            "$i",
            -1,
            0,
            len(cmds) - 1,
        )

        specs = {"libFuzzer": specs}
        return (cmds, specs)

    def generate_one(self, input_corpus: str, output_corpus: str) -> str:
        cmd = "$appname -use_value_profile=1 -cross_over_uniform_dist=1 -max_len=500 "
        cmd += "-rss_limit_mb=0 -timeout=10 -create_missing_dirs=1 "
        run_dir = os.path.dirname(output_corpus)
        artifacts_dir = os.path.join(run_dir, "artifacts") + os.sep
        log_path = os.path.join(run_dir, "libfuzzer$i.log")
        cmd += f"-artifact_prefix={artifacts_dir} {output_corpus} {input_corpus} 2>&1 | tee {log_path}"
        return cmd

    def stats_cmd(self, sync_dir: str) -> Optional[str]:
        """
        libFuzzer has no separate stats command
        """
        return None

    def make_replacements(
        self, cmds: List[str], builds: Dict[BuildType, str]
    ) -> Dict[str, Dict[str, str]]:
        specs = {}

        base_cmd = cmds[0]
        del cmds[0]

        sanitizer_counts = {bt: 0 for bt in builds if bt.is_static_sanitizer()}
        if BuildType.BASIC in builds:
            basic_count = self.count - len(sanitizer_counts)
            if basic_count < 0:
                raise FuzzerCmdError(
                    f"count={self.count} < len(sanitizer)={len(sanitizer_counts)}"
                )
        else:
            basic_count = 0

        if basic_count > 0:
            cmd = base_cmd.replace(" ", f" -fork={basic_count} -ignore_crashes=1 ", 1)
            cmd_with_basic_build = cmd.replace("$appname", builds[BuildType.BASIC])
            cmds.append(cmd_with_basic_build)
            specs[builds[BuildType.BASIC]] = self.output_corpus

        if not sanitizer_counts:
            return specs

        cmds_left = self.count - basic_count

        # populate sanitizers evenly
        while cmds_left > 0:
            for san in sanitizer_counts:
                sanitizer_counts[san] += 1
                cmds_left -= 1
                if cmds_left < 1:
                    break

        for san, count in sanitizer_counts.items():
            cmd = base_cmd.replace(" ", f" -fork={count} -ignore_crashes=1 ", 1)
            cmd_with_san_build = cmd.replace("$appname", builds[san])
            cmds.append(cmd_with_san_build)
            specs[builds[san]] = self.output_corpus

        return specs

    def make_one_tmux_capture_pane_cmd(
        self, tmux_session_name: str, window_index: int
    ) -> str:
        """
        Generate one tmux capture-pane command to get fuzzer log on stdout
        """
        return (
            f"""tmux capture-pane -e -t {tmux_session_name}:{window_index} -S -5 -p"""
        )
