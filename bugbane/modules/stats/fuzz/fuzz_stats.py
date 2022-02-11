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

from dataclasses import dataclass
from time import time

from ..stats import Stats, StatsError


class FuzzStatsError(StatsError):
    """Exception class for errors in FuzzStats class"""


@dataclass
class FuzzStats(Stats):
    num_instances: int = 0
    execs: int = 0
    crashes: int = 0
    hangs: int = 0
    execs_per_sec_sum: float = 0.0
    last_path_timestamp: int = 0
    start_timestamp: int = int(time())

    def clear(self):
        self.num_instances = 0
        self.execs = 0
        self.crashes = 0
        self.hangs = 0
        self.execs_per_sec_sum = 0.0
        self.last_path_timestamp = 0
        self.start_timestamp = int(time())

    def to_dict(self) -> dict:
        self._ensure_format()
        return {
            "num_instances": self.num_instances,
            "execs": self.execs,
            "crashes": self.crashes,
            "hangs": self.hangs,
            "execs_per_sec_sum": self.execs_per_sec_sum,
            "execs_per_sec_avg": self.execs_per_sec_avg,
        }

    def _ensure_format(self):
        self.num_instances = int(self.num_instances)
        self.execs = int(self.execs)
        self.crashes = int(self.crashes)
        self.hangs = int(self.hangs)
        self.execs_per_sec_sum = round(self.execs_per_sec_sum, 1)
        self.last_path_timestamp = int(self.last_path_timestamp)
        self.start_timestamp = int(self.start_timestamp)

    @property
    def execs_per_sec_avg(self) -> float:
        """Average fuzzer speed, execs per second"""
        avg = self.execs_per_sec_sum
        if self.num_instances > 0:
            avg = avg / self.num_instances
        return avg

    def add_stats_from(self, *others):
        """
        *others: iterable of FuzzStats
        """
        for other in others:
            self.num_instances += other.num_instances
            self.execs += other.execs
            self.crashes += other.crashes
            self.hangs += other.hangs
            self.execs_per_sec_sum += other.execs_per_sec_sum

    def fuzzer_type(self) -> str:
        """
        Return fuzzer type for which this FuzzStats class is compatible
        """
        return None
