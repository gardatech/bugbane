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

from typing import Optional

import logging

log = logging.getLogger(__name__)

from bugbane.modules.format import metric_try_to_float

from .fuzz_stats import FuzzStats, FuzzStatsError
from .factory import FuzzStatsFactory


class AFLplusplusFuzzStatsError(FuzzStatsError):
    """Exceptions that happen in AFLplusplusFuzzStats class"""


@FuzzStatsFactory.register("AFL++")
class AFLplusplusFuzzStats(FuzzStats):
    stats_file_name = "fuzzer_stats"

    def fuzzer_type(self) -> str:
        return "AFL++"

    def _load_multidict(self, data: dict):
        for subdir, fuzz_stats in data.items():
            self.num_instances += 1

            execs = fuzz_stats.get("execs_done", 0)
            self.execs += execs

            execs_per_sec = fuzz_stats.get("execs_per_sec", 0.0)
            self.execs_per_sec_sum += execs_per_sec

            crashes = fuzz_stats.get("unique_crashes", 0)
            self.crashes += crashes

            hangs = fuzz_stats.get("unique_hangs", 0)
            self.hangs += hangs

            start_time = fuzz_stats.get("start_time", 0)
            if self.start_timestamp >= start_time:
                self.start_timestamp = start_time

            last_path = fuzz_stats.get("last_path", 0)
            if self.last_path_timestamp < last_path:
                self.last_path_timestamp = last_path

            log.verbose3(
                "Loaded %d execs, %d crashes and %d hangs from subdir %s",
                execs,
                crashes,
                hangs,
                subdir,
            )

    def read_one(self, file_path: str) -> Optional[dict]:
        """
        For AFL-like fuzzers (AFL, AFL++, WinAFL, ...)
        Returns dict with fuzzer stats.
        """
        log.debug("loading fuzzer stats from file '%s'", file_path)

        try:
            data = open(file_path, "rt").readlines()
        except OSError as e:
            raise AFLplusplusFuzzStatsError(
                f"error while reading fuzzer stats file '{file_path}': {e}"
            ) from e

        stats = {}
        try:
            for i, line in enumerate(data):
                if len(line) < 3:
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = metric_try_to_float(v.strip())
                stats[k] = v
        except ValueError as e:
            raise AFLplusplusFuzzStatsError(
                f"malformed fuzzer stat in file '{file_path}', line {i} ({e})"
            ) from e

        log.debug("loaded %d stats from file '%s'", len(stats), file_path)
        return stats
