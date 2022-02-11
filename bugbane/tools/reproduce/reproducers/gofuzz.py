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

from typing import Optional, List, Tuple

import re
import glob
import logging


log = logging.getLogger(__name__)

from bugbane.modules.process import make_env_shell_str

from .factory import ReproducerFactory
from .reproducer import Reproducer, ReproducerError
from ..issue_card import IssueCard
from ..verdict import Verdict


@ReproducerFactory.register("go-fuzz")
class GoFuzzReproducer(Reproducer):
    """
    go-fuzz reproducer that only collects reproduce results previously saved by fuzzer
    """

    def run_binary_on_samples(
        self, binary_path: str, crashes_mask: Optional[str], hangs_mask: Optional[str]
    ) -> List[IssueCard]:
        crashers = glob.glob(crashes_mask)
        cards = self.collect_crashers(binary_path, crashers)
        return cards

    def collect_crashers(
        self, binary_path: str, crashers: List[str]
    ) -> List[IssueCard]:
        """
        For each crasher in `crashers` collect program output,
        extract bug locations, return list of IssueCard
        """
        cards: List[IssueCard] = []

        for crasher in crashers:
            output_file_path, output = self.load_crasher_output(crasher)
            verdict = self.make_verdict(output)
            if verdict.value <= Verdict.HANG.value:
                continue

            card = IssueCard(
                reproduce_cmd=f"cat {output_file_path}",
                reproduce_env=make_env_shell_str(self.run_env),
                output=output,
                binary=binary_path,
                sample=crasher,
                verdict=verdict,
            )
            cards.append(card)

        return cards

    def load_crasher_output(self, crasher: str) -> Tuple[str, str]:
        """
        Load output matching given crasher.
        `crasher` is path to crasher file
        """

        output_file_path = crasher + ".output"
        try:
            with open(output_file_path, "rt", encoding="utf-8") as f:
                output = f.read()
        except OSError as e:
            raise ReproducerError(
                f"wasn't able to read crasher output file {output_file_path}. Message: {e}"
            ) from e

        return (output_file_path, output)

    def make_verdict(self, output: str) -> Verdict:
        """Convert crasher output to Verdict"""
        exit_code = self._get_exit_code_from_output(output)
        verdict = Verdict.from_run_results(
            exit_code=exit_code, is_hang=None, output=output
        )
        return verdict

    def _get_exit_code_from_output(self, output: str) -> Optional[int]:
        """
        Extract exit code from output.
        Return None if output is empty or None
        """
        re_exit_code = re.compile(r"^exit status (\d+)$")
        m = re_exit_code.match(output)
        if m is None:
            return None
        return int(m.group(1))
