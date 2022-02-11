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

from typing import Callable, Tuple, Dict, List, Optional

import logging

log = logging.getLogger(__name__)

import glob

from ..issue_card import IssueCard
from ..verdict import Verdict
from .reproducer import Reproducer
from .factory import ReproducerFactory

from bugbane.modules.process import (
    make_env_shell_str,
    prepare_run_args_for_shell,
    run_interactive_shell_cmd,
    run_shell_cmd,
)


@ReproducerFactory.register_default()
class DefaultReproducer(Reproducer):
    """
    Reproducer that runs tested application
    """

    def run_binary_on_samples(
        self, binary_path: str, crashes_mask: Optional[str], hangs_mask: Optional[str]
    ) -> List[IssueCard]:
        cards: List[IssueCard] = []
        cards.extend(self.run_binary_on_crashes(binary_path, crashes_mask))
        cards.extend(self.run_binary_on_hangs(binary_path, hangs_mask))
        return cards

    def run_binary_on_crashes(
        self, binary_path: str, mask: Optional[str]
    ) -> List[IssueCard]:
        cards: List[IssueCard] = []
        samples = self.mask_to_samples(mask)
        for sample in samples:
            cmd = self.make_basic_run_cmd(binary_path, sample)
            card = self.run(cmd, binary_path, sample, self.one_run_try)
            if card.verdict.value <= Verdict.CRASH_GENERIC.value:
                cmd = self.make_gdb_run_cmd(binary_path, sample)
                card = self.run(cmd, binary_path, sample, self.one_run_try)
            if card.verdict.value >= Verdict.HANG.value:
                cards.append(card)
        return cards

    def run_binary_on_hangs(
        self, binary_path: str, mask: Optional[str]
    ) -> List[IssueCard]:
        cards: List[IssueCard] = []
        samples = self.mask_to_samples(mask)
        for sample in samples:
            cmd = self.make_gdb_run_cmd_for_hang(binary_path, sample)
            card = self.run(cmd, binary_path, sample, self.one_run_try_hang)
            if card.verdict.value >= Verdict.HANG.value:
                cards.append(card)
        return cards

    def mask_to_samples(self, mask: Optional[str]) -> List[str]:
        """Return sorted(glob.glob(mask)) if mask is not empty/None"""
        if not mask:
            return []
        return sorted(glob.glob(mask))

    def run(
        self,
        cmd: str,
        binary_path: str,
        sample_path: str,
        run_method: Callable[[str, Dict[str, str]], Tuple[Verdict, str]],
    ) -> IssueCard:
        """
        Reproduce one binary on one sample up to self.num_tries times
        or until a bug is detected.
        Return partially filled IssueCard (without title and bug location)
        """

        for try_num in range(1, self.num_tries + 1):
            log.verbose3("%s run: %s (try #%d)", self.__class__.__name__, cmd, try_num)
            verdict, output = run_method(cmd, self.run_env)

            if verdict.value >= Verdict.HANG.value:
                break

        return IssueCard(
            reproduce_cmd=cmd,
            reproduce_env=make_env_shell_str(self.run_env),
            output=output,
            binary=binary_path,
            sample=sample_path,
            verdict=verdict,
        )

    def one_run_try(self, cmd: str, run_env: Dict[str, str]) -> Tuple[Verdict, str]:
        """
        Run given cmd with specified extra env vars run_env.
        Return Verdict based on run results and command output
        """
        ex_code, is_hang, output = run_shell_cmd(cmd, run_env, self.timeout_sec)
        output = output.decode(errors="replace")
        verdict = self.make_verdict(ex_code, is_hang, output)
        return (verdict, output)

    def one_run_try_hang(
        self, cmd: str, run_env: Dict[str, str]
    ) -> Tuple[Verdict, str]:
        """
        Custom implementation of one_run_try with different run function
        """
        ex_code, output = run_interactive_shell_cmd(cmd, run_env)
        output = output.decode(errors="replace")
        verdict = self.make_verdict(
            exit_code=ex_code, is_hang="<HANG_START>" in output, output=output
        )
        return (verdict, output)

    def make_verdict(self, exit_code: int, is_hang: bool, output: str):
        """Convert application run results to Verdict"""
        verdict = Verdict.from_run_results(
            exit_code=exit_code, is_hang=is_hang, output=output
        )
        return verdict

    def make_basic_run_cmd(
        self,
        binary_path: str,
        sample_path: str,
    ) -> str:
        """
        Generate simplest run command: binary_path and run_args
        Use for first run of tested application on given sample.
        Run output may include sanitizer stacktrace or generic error message.
        """
        return binary_path + " " + self.prep_run_args(sample_path)

    def make_gdb_run_cmd(self, binary_path: str, sample_path: str) -> str:
        """
        Create command to run binary with given sample as input via gdb.
        Use for cases where BasicReproducer returned program output containing
        generic error message without stack trace.
        Output may contain gdb stack trace of crash.
        """
        cmd = f"gdb --batch -q --ex 'r {self.prep_run_args(sample_path)}'"
        cmd += f" --ex 'bt' --ex 'quit' {binary_path} 0</dev/null"
        return cmd

    def make_gdb_run_cmd_for_hang(self, binary_path: str, sample_path: str) -> str:
        """
        Create long gdb command to run binary with given hang sample as input.
        The command includes odd number of "step" and "info line" instructions to detect hang location.
        Program output may contain gdb hang stack trace
        """

        kill_after = max(int(self.timeout_sec * 0.9), 4)
        run_before_stepping_sec = max(int(self.timeout_sec * 0.25), 2)

        cmd = f"timeout --kill-after {kill_after}s -s SIGINT {run_before_stepping_sec}s gdb -q "
        cmd += f"--ex 'r {self.prep_run_args(sample_path)}'"

        cmd += ' --ex "echo <HANG_START>\\n"'

        line_count = [11, 111, 1111, 111, 11]
        for run_lines in line_count:
            cmd += f' --ex "step {run_lines}" --ex "info line"'

        cmd += f' --ex "echo <HANG_END>\\n" --ex "q" {binary_path} 0</dev/null'

        return cmd

    def prep_run_args(self, sample_path: str) -> str:
        """
        Generate shell-compatible run arguments replacing @@ with sample_path.
        """
        return prepare_run_args_for_shell(self.run_args, sample_path)
