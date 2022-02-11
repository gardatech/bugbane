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

import re
import time

import logging

from bugbane.modules.file_utils import read_last_lines
from bugbane.modules.format import golang_duration_to_seconds

log = logging.getLogger(__name__)

from .fuzz_stats import FuzzStats, FuzzStatsError
from .factory import FuzzStatsFactory


class GoFuzzFuzzStatsError(FuzzStatsError):
    """Exceptions that happen in GoFuzzFuzzStats class"""


@FuzzStatsFactory.register("go-fuzz")
class GoFuzzFuzzStats(FuzzStats):
    stats_file_name = "go-fuzz.log"

    def fuzzer_type(self) -> str:
        return "go-fuzz"

    def _load_multidict(self, data: dict):
        for subdir, fuzz_stats in data.items():
            self.num_instances += fuzz_stats.get("num_workers", 0)

            execs = fuzz_stats.get("execs", 0)
            self.execs += execs

            execs_per_sec = fuzz_stats.get("execs_per_sec", 0.0)
            self.execs_per_sec_sum += execs_per_sec

            crashes = fuzz_stats.get("crashes", 0)
            self.crashes += crashes

            hangs = fuzz_stats.get("timeouts", 0)
            self.hangs += hangs

            start_time = fuzz_stats.get("start_time", 0)
            if self.start_timestamp >= start_time:
                self.start_timestamp = start_time

            last_path = fuzz_stats.get("last_path", 0)
            if self.last_path_timestamp < last_path:
                self.last_path_timestamp = last_path

            log.verbose3(
                "Loaded %d execs, %d crashes and/or hangs from subdir %s",
                execs,
                crashes,
                subdir,
            )

    def read_one(self, file_path: str) -> Optional[dict]:
        """
        Reads go-fuzz log file.
        Returns dict with fuzzer stats.
        """
        log.debug("loading fuzzer stats from file '%s'", file_path)

        re_all_stats = re.compile(
            r"^(\S+\s+\S+)\s+.*?workers:\s+(\d+).*?corpus:\s+(\d+)\s+\((.*?)\s+ago\).*?crashers:\s+(\d+).*?execs:\s+(\d+)\s+\((\d+)/sec\).*?uptime:\s+(\S+)\s*?$",
        )
        # groups: 1=date&time 2=workers 3=total_samples 4=lath_sample_time_delta (e.g. "26m27s") 5=crashes 6=execs 7=execs_per_sec_avg 8=duration (e.g. "2h10m")

        stats = {}

        try:
            num_lines = 3
            lines = read_last_lines(
                file_path, num_lines=num_lines, expected_line_size=160
            )
            for line in reversed(lines):
                m = re_all_stats.match(line)
                if m:
                    break

            if m is None:
                raise GoFuzzFuzzStatsError(
                    f"wasn't able to match regex to any of the last {num_lines} lines"
                    " of log file. Bad go-fuzz log file?"
                )

            num_workers = int(m.group(2))
            last_path_time_delta = golang_duration_to_seconds(m.group(4))
            crashes = int(m.group(5))
            execs = int(m.group(6))
            execs_per_sec = int(m.group(7))
            duration = golang_duration_to_seconds(m.group(8))
        except OSError as e:
            raise GoFuzzFuzzStatsError(
                f"error while reading fuzzer stats file '{file_path}': {e}"
            ) from e
        except (ValueError, AttributeError) as e:
            raise GoFuzzFuzzStatsError(
                f"malformed fuzzer stat in file '{file_path}' (last line). Error: {e}"
            ) from e

        stats["num_workers"] = num_workers
        stats["execs"] = execs
        stats["execs_per_sec"] = execs_per_sec
        stats["timeouts"] = 0  # TODO: does golang have timeouts/hangs?
        stats["crashes"] = crashes

        now = int(time.time())
        start_time = now - duration
        last_path = now - last_path_time_delta
        stats["start_time"] = start_time
        stats["last_path"] = last_path

        log.debug("loaded %d stats from file '%s'", len(stats), file_path)
        return stats
