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
from abc import ABC, abstractmethod

from bugbane.modules.build_type import BuildType

from bugbane.modules.string_utils import replace_part_in_str_list


class FuzzerCmdError(Exception):
    """Exception for errors in FuzzerCmd class."""


class FuzzerCmd(ABC):
    """
    ABC for generating commands to start fuzzing.
    """

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
        """
        Generate commands to run fuzzer on `count` cores.
        Return tuple: (cmds, reproduce_specs)
        """
        cmds = [
            self.generate_one(input_corpus, output_corpus, run_env)
            for _ in range(count)
        ]
        replace_part_in_str_list(cmds, "$run_args", run_args, -1, 0, count - 1)
        specs = self.make_replacements(cmds, builds, dict_path, timeout_ms)
        return cmds, specs

    @abstractmethod
    def generate_one(
        self, input_corpus: str, output_corpus: str, run_env: Dict[str, str]
    ) -> str:
        """
        Generate one basic fuzzer command.
        Returned result may contain:
            $name - will be replaced later with fuzzer instance name
            $appname - replaced later with tested app name/path
            $run_args - arguments to run application with one sample, possibly containing @@
            $i - index number of fuzzer instance
        """

    @abstractmethod
    def make_replacements(
        self,
        cmds: List[str],
        builds: Dict[BuildType, str],
        dict_path: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Assign builds and different cmdline arguments for fuzzer commands.
        Commands are replaced in place.
        Return reproduce spec: {"fuzzer_type": {"binary_path": ["samples_root_dir", ...]}}
        """

    @abstractmethod
    def add_timeout_to_cmd(self, cmd: str, timeout_ms: Optional[int]) -> str:
        """
        Add timeout option to fuzzer `cmd`.
        Return new fuzzer cmd.
        """

    @abstractmethod
    def stats_cmd(self, sync_dir: str) -> Optional[str]:
        """
        Return command that checks fuzzer statistics (e.g. afl-whatsup).
        Return None if no such command exists for this fuzzer.
        """

    def make_tmux_screen_capture_cmds(
        self,
        num_windows: int,
        tmux_socket_name: Optional[str] = None,
        tmux_session_name: Optional[str] = None,
    ) -> List[str]:
        """
        Generate shell commands with tmux capture-pane and possible "beautifying" greps
        to capture output of stats utility and fuzzer screens/logs.
        """
        tmux_socket_name = tmux_socket_name or "fuzz"
        tmux_session_name = tmux_session_name or "fuzz"

        cmds = []
        for i in range(1, num_windows + 1):
            cmd = self.make_one_tmux_capture_pane_cmd(tmux_socket_name, tmux_session_name, i)
            cmds.append(cmd)

        return cmds

    @abstractmethod
    def make_one_tmux_capture_pane_cmd(
        self, tmux_socket_name: str, tmux_session_name: str, window_index: int
    ) -> str:
        """
        Generate one tmux capture-pane command with possible "beautifying" greps
        to get fuzzer screen/log/stats dump on stdout.
        """
