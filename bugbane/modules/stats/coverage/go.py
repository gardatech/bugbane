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
import logging

log = logging.getLogger()

from .coverage_stats import CoverageStats, CoverageStatsError
from .factory import CoverageStatsFactory


class GoCoverageStatsError(CoverageStatsError):
    """Exceptions that happen in GoCoverageStats class"""


@CoverageStatsFactory.register("go-tool-cover")
class GoCoverageStats(CoverageStats):
    """
    Collects coverage information from file generated with:
    ```
    go tool cover -func=out/coverprofile.processed
    ```
    """

    stats_file_name = "summary.txt"

    def get_tool_name(self):
        return "go tool cover"

    def read_from_str(self, s: str) -> Optional[dict]:
        """
        Parse data previously read from coverage stats file.
        Return coverage stats.
        Expected format:
        ```
        /src/go/fuzz.go:5:      Fuzz            100.0%
        /src/go/fuzzable.go:7:  check_index     50.0%
        /src/go/fuzzable.go:13: recursive_sum   62.5%
        /src/go/fuzzable.go:27: busy_loop       68.8%
        /src/go/fuzzable.go:52: Parse           80.0%
        total:                  (statements)    70.3%
        ```
        """

        lines = s.rstrip(" \n").splitlines()
        if not lines:
            raise GoCoverageStatsError("empty coverage stats")

        last = lines[-1]

        re_total_cov = re.compile(r"^total:\s+\(statements\)\s+(\S+)%")
        m = re_total_cov.match(last)
        if m is None:
            raise GoCoverageStatsError("'total' line not found in coverage stats")

        matched = m.group(1)
        cov = matched.replace(",", ".")
        cov = float(cov)

        if cov > 100.0 or cov < 0.0:
            raise GoCoverageStatsError(f"invalid coverage percent '{matched}'")

        cov_line_total = 10000
        cov_line_cover = int(cov_line_total * cov / 100.0)

        totals = {"line_total": cov_line_total, "line_cover": cov_line_cover}
        return totals
