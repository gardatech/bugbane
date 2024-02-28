# Copyright 2022-2024 Garda Technologies, LLC. All rights reserved.
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

from typing import Optional, Dict

import os
import re

from bugbane.modules.format_utils import golang_duration_to_seconds
from bugbane.modules.log import getLogger

log = getLogger(__name__)

from .gofuzz import GoFuzzFuzzStats
from .fuzz_stats import FuzzStatsError
from .factory import FuzzStatsFactory


class GoTestFuzzStatsError(FuzzStatsError):
    """Exception class for errors in LibFuzzerFuzzStats."""


@FuzzStatsFactory.register("go-test")
class GoTestFuzzStats(GoFuzzFuzzStats):
    """
    FuzzStats for `go test` native fuzzer (for go > 1.18).
    Stats are read from fuzzer log file.
    """

    stats_file_name = "go-test-fuzz.log"

    def fuzzer_type(self) -> str:
        return "go-test"

    def read_one(self, file_path: str) -> Optional[Dict]:
        """
        Reads `go test` fuzzing log file.
        Returns dict with fuzzer stats.
        """

        # XXX: this code is similar to LibFuzzerFuzzStats.read_one
        # except for regexes and early exit on "FAIL" string

        log.debug("loading fuzzer stats from file '%s'", file_path)

        re_num_forks = re.compile(r"^.*?now fuzzing with (\d+) workers")
        re_all_stats = re.compile(
            r"^.*?:\s+elapsed:\s+(\S+),\s+execs:\s+(\d+)\s+\((\d+)\/sec\).*?total:\s+(\d+)\).*?$",
        )  # groups: 1=duration_str 2=execs 3=execs_per_sec 4=num_samples

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

                    if line.strip() == "FAIL":
                        crashes = (
                            1  # `go test` fuzzer currently exits after first found bug
                        )
                        break

                    m = re_all_stats.match(line)
                    if m is None:
                        continue
                    last_stats_match = m

                    samples = int(m.group(4))
                    duration = golang_duration_to_seconds(m.group(1))

                    if samples > max_samples:
                        max_samples = samples
                        max_samples_duration = duration

        except OSError as e:
            raise GoTestFuzzStatsError(
                f"error while reading fuzzer stats file '{file_path}': {e}"
            ) from e
        except ValueError as e:
            raise GoTestFuzzStatsError(
                f"malformed fuzzer stat in file '{file_path}', line {linenum} ({e})"
            ) from e

        if last_stats_match is not None:
            m = last_stats_match
            execs = int(m.group(2))
            execs_per_sec = int(m.group(3))

        stats["num_workers"] = num_forks
        stats["execs"] = execs
        stats["execs_per_sec"] = execs_per_sec
        stats["timeouts"] = timeouts  # TODO: separate crashes from hangs if possible
        stats["crashes"] = crashes

        start_time = last_mod_time - duration
        stats["start_time"] = start_time
        stats["last_path"] = start_time + max_samples_duration

        log.debug("loaded %d stats from file '%s'", len(stats), file_path)
        return stats
