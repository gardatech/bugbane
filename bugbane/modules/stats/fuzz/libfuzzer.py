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

import os
import re

import logging

log = logging.getLogger(__name__)

from .fuzz_stats import FuzzStats, FuzzStatsError
from .factory import FuzzStatsFactory


class LibFuzzerFuzzStatsError(FuzzStatsError):
    """Exceptions that happen in LibFuzzerFuzzStats class"""


@FuzzStatsFactory.register("libFuzzer")
class LibFuzzerFuzzStats(FuzzStats):
    stats_file_name = "libfuzzer*.log"

    def fuzzer_type(self) -> str:
        return "libFuzzer"

    def _load_multidict(self, data: dict):
        for subdir, fuzz_stats in data.items():
            self.num_instances += fuzz_stats.get("num_forks", 0)

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
                "Loaded %d execs, %d crashes and %d hangs from subdir %s",
                execs,
                crashes,
                hangs,
                subdir,
            )

    def read_one(self, file_path: str) -> Optional[dict]:
        """
        Reads libFuzzer log file.
        Returns dict with fuzzer stats.
        """
        log.debug("loading fuzzer stats from file '%s'", file_path)

        re_num_forks = re.compile(r"^INFO: .*?fork=(\d+)")
        re_all_stats = re.compile(
            r"^#(\d+):.*?\s+corp: (\d+)\s+.*?exec/s:?\s+(\d+)\s+oom/timeout/crash:\s+\d+/(\d+)/(\d+)\s+\s*?time:\s+(\d+).*?$",
        )  # groups: 1=total_execs 2=total_samples 3=execs_per_sec 4=timeouts 5=crashes 6=duration

        stats = {}

        num_forks = 0
        max_samples = 0
        max_samples_duration = 0
        execs = 0
        samples = 0
        execs_per_sec = 0
        timeouts = 0
        crashes = 0
        duration = 0

        last_stats_match = None

        last_mod_time = int(os.path.getmtime(file_path))

        try:
            with open(file_path, "rt") as f:
                for linenum, line in enumerate(f, start=1):
                    if num_forks < 1:
                        m = re_num_forks.match(line)
                        if m is not None:
                            num_forks = int(m.group(1))
                            continue

                    m = re_all_stats.match(line)
                    if m is None:
                        continue
                    last_stats_match = m

                    samples = int(m.group(2))
                    duration = int(m.group(6))

                    if samples >= max_samples:
                        max_samples = samples
                        max_samples_duration = duration

        except OSError as e:
            raise LibFuzzerFuzzStatsError(
                f"error while reading fuzzer stats file '{file_path}': {e}"
            ) from e
        except ValueError as e:
            raise LibFuzzerFuzzStatsError(
                f"malformed fuzzer stat in file '{file_path}', line {linenum} ({e})"
            ) from e

        if last_stats_match is not None:
            m = last_stats_match
            execs = int(m.group(1))
            execs_per_sec = int(m.group(3))
            timeouts = int(m.group(4))
            crashes = int(m.group(5))

        stats["num_forks"] = num_forks
        stats["execs"] = execs
        stats["execs_per_sec"] = execs_per_sec
        stats["timeouts"] = timeouts
        stats["crashes"] = crashes

        start_time = last_mod_time - duration
        stats["start_time"] = start_time
        stats["last_path"] = start_time + max_samples_duration

        log.debug("loaded %d stats from file '%s'", len(stats), file_path)
        return stats
