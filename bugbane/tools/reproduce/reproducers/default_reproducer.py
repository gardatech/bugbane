# Copyright 2022-2026 Garda Technologies, LLC. All rights reserved.
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

from typing import Callable, Tuple, Dict, List, Optional, Iterable, Sequence

import re

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.process import (
    make_env_shell_str,
    prepare_run_args_for_shell,
    run_interactive_shell_cmd,
    run_shell_cmd,
)

from ..issue_card import IssueCard
from ..verdict import Verdict
from .reproducer import Reproducer
from .factory import ReproducerFactory

re_gdb_traceback = re.compile(
    r"Traceback \(most recent call last\):.*?(?:/gdb/auto-load/|/gdb/python/|/gcc/python/|/gdb/command/).*?KeyboardInterrupt",
    re.DOTALL,
)


def output_has_gdb_traceback(output: str) -> bool:
    """Return True when gdb's python traceback is found in the `output`."""
    return re_gdb_traceback.search(output) is not None


@ReproducerFactory.register_default()
class DefaultReproducer(Reproducer):
    """
    Reproducer that runs tested application.
    """

    def run_binary_on_samples(
        self,
        binary_path: str,
        crashes: Iterable[str],
        hangs: Iterable[str],
        hang_reproduce_limit: int,
        hang_confirm_tries: int,
        hang_gdb_cleanup_tries: int,
    ) -> List[IssueCard]:
        cards: List[IssueCard] = []
        cards.extend(self.run_binary_on_crashes(binary_path, crashes))
        cards.extend(
            self.run_binary_on_hangs(
                binary_path,
                hangs,
                hang_reproduce_limit,
                hang_confirm_tries,
                hang_gdb_cleanup_tries,
            )
        )
        return cards

    def run_binary_on_crashes(
        self, binary_path: str, samples: Iterable[str]
    ) -> List[IssueCard]:
        cards: List[IssueCard] = []
        for sample in samples:
            cmd = self.make_basic_run_cmd(binary_path, sample)
            card = self.run(cmd, binary_path, sample, self.one_run_try)
            if card.verdict.value[0] <= Verdict.CRASH_GENERIC.value[0]:
                cmd = self.make_gdb_run_cmd(binary_path, sample)
                card = self.run(cmd, binary_path, sample, self.one_run_try)
            if card.verdict.value[0] >= Verdict.HANG.value[0]:
                cards.append(card)
        return cards

    def run_binary_on_hangs(
        self,
        binary_path: str,
        samples: Iterable[str],
        hang_reproduce_limit: int,
        hang_confirm_tries: int,
        hang_gdb_cleanup_tries: int,
    ) -> List[IssueCard]:
        """
        Checks if binary hangs on given samples using gdb.

        Has two mechanisms against false positives:
        1. Performs up to `hang_confirm_tries + 1` runs of tested app. Any of tries
           doesn't cause hang -> it's FP. This is to prevent situations when tested app
           hangs due to host experiencing intermittent high load.
        2. Restarts runs which would later be improperly classified as crashes due to
           having tracebacks of gdb's own python. Does so up to `hang_gdb_cleanup_tries`.
           If the traceback persists, the issue is kept as is for better review.
        """
        cards: List[IssueCard] = []
        for num, sample in enumerate(samples, start=1):
            if num > hang_reproduce_limit:
                break

            card = None

            # can be zero, but we need at least one run in total
            one_hang_attempt_limit = hang_confirm_tries + 1
            hang_attempts_left = one_hang_attempt_limit

            # can be zero, and it's fine:
            hang_gdb_cleanup_attempts_left = hang_gdb_cleanup_tries

            max_attempts = hang_attempts_left + hang_gdb_cleanup_attempts_left

            try_num = 0
            while hang_attempts_left > 0:
                hang_attempts_left -= 1
                try_num += 1

                cmd = self.make_gdb_run_cmd_for_hang(binary_path, sample)
                card = self.run(
                    cmd, binary_path, sample, self.one_run_try_hang, num_tries=1
                )

                if (
                    card.verdict is None
                    or card.verdict.value[0] < Verdict.HANG.value[0]
                ):
                    # doesn't cause hang on any iteration -> it's not a hang, a temporary fluke
                    log.verbose2(
                        "Hang not detected on attempt %d/%d. Discarding hang sample '%s' as non-reproducible...",
                        try_num,
                        max_attempts,
                        sample,
                    )
                    card = None
                    break

                if hang_gdb_cleanup_attempts_left > 0:
                    if output_has_gdb_traceback(card.output):
                        log.verbose2(
                            "Possible hang contains gdb's own python traceback (hang confirmation attempt: %d/%d, traceback detections: %d/%d), attempting another run...",
                            try_num,
                            max_attempts,
                            hang_gdb_cleanup_tries - hang_gdb_cleanup_attempts_left + 1,
                            hang_gdb_cleanup_tries,
                        )

                        hang_gdb_cleanup_attempts_left -= 1
                        # add back one more attempt, since we just consumed it on this check:
                        hang_attempts_left += 1

                        # traceback present = it's probably a false positive
                        # restart for a chance get rid of the gdb traceback
                        continue

                # here, we either have no gdb traceback, or ran out of chances to remove it
                # retry the iteration to confirm it wasn't a fluke
                if hang_attempts_left > 0:
                    extra_message = ", retrying..."
                else:
                    extra_message = " => Confirmed and kept"
                log.verbose2(
                    "Hang detected for sample '%s' on attempt %d/%d%s",
                    sample,
                    try_num,
                    max_attempts,
                    extra_message,
                )

            if card is not None:
                cards.append(card)

        return cards

    def run(
        self,
        cmd: str,
        binary_path: str,
        sample_path: str,
        run_method: Callable[[str, Dict[str, str]], Tuple[Verdict, str]],
        num_tries: Optional[int] = None,
    ) -> IssueCard:
        """
        Reproduce one binary on one sample up to num_tries times (or
        self.num_tries if not passed) until a bug is detected.
        Return partially filled IssueCard (without title and bug location)
        """
        if num_tries is None:
            num_tries = self.num_tries
        tries = max(1, num_tries)

        for try_num in range(1, tries + 1):
            log.verbose3("%s run: %s (try #%d)", self.__class__.__name__, cmd, try_num)
            verdict, output = run_method(cmd, self.run_env)

            if verdict.value[0] >= Verdict.HANG.value[0]:
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
        output = (output or b"").decode(errors="replace")
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

    def make_verdict(
        self, exit_code: Optional[int], is_hang: bool, output: Optional[str]
    ):
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
        cmd = "gdb --batch -q"
        cmd += " --ex 'set filename-display absolute'"
        cmd += f" --ex 'r {self.prep_run_args(sample_path)}'"
        cmd += " --ex 'bt'"
        cmd += f" --ex 'quit' {binary_path} 0</dev/null"
        return cmd

    def make_gdb_run_cmd_for_hang(self, binary_path: str, sample_path: str) -> str:
        """
        Create long gdb command to run binary with given hang sample as input.
        The command includes odd number of "step" and "info line" instructions to detect hang location.
        Program output may contain gdb hang stack trace
        """

        kill_after = max(int(self.timeout_sec * 0.9), 4)
        run_before_stepping_sec = max(int(self.timeout_sec * 0.25), 2)

        cmd = f"timeout --kill-after {kill_after}s -s SIGINT {run_before_stepping_sec}s gdb -q"
        cmd += " --ex 'set filename-display absolute'"
        cmd += f" --ex 'r {self.prep_run_args(sample_path)}'"

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

    @classmethod
    def reproduce_cmd_matchers(cls) -> Sequence[str]:
        return ["artifacts/", "crashes/id", "hangs/id"]

    @classmethod
    def can_run_tested_app(cls) -> bool:
        return True
