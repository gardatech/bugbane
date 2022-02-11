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

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..issue_card import IssueCard


class ReproducerError(Exception):
    """Exception representing errors in Reproducer subclasses"""


class Reproducer(ABC):
    """
    ABC for confirming bugs in tested applications.
    Should detect both crashes and hangs
    """

    def __init__(self):
        self.run_args: List[str] = []
        self.run_env: Dict[str, str] = {}
        self.num_tries: int = 3
        self.timeout_sec: int = 10

    def set_run_args(self, run_args: List[str]):
        self.run_args = run_args

    def set_run_env(self, run_env: Dict[str, str]):
        self.run_env = run_env

    def set_num_tries(self, num_tries: int):
        self.num_tries = num_tries

    def set_timeout(self, timeout_seconds: int):
        self.timeout_sec = timeout_seconds

    @abstractmethod
    def run_binary_on_samples(
        self, binary_path: str, crashes_mask: Optional[str], hangs_mask: Optional[str]
    ) -> List[IssueCard]:
        """
        Run binary specified by binary_path on each sample matching crashes_mask or hangs_mask.
        If any mask is missing/empty, then nothing should be done for it.
        Masks may specify one file.
        Return list of IssueCard
        """
