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

from bugbane.modules.format import squeeze_spaces

from .coverage_stats import CoverageStats, CoverageStatsError
from .factory import CoverageStatsFactory


class LLVMSummaryCoverageStatsError(CoverageStatsError):
    """Exceptions that happen in LLVMSummaryCoverageStats class"""


@CoverageStatsFactory.register("llvm-summary")
class LLVMSummaryCoverageStats(CoverageStats):
    """
    Collects coverage information from summary.txt file, produced by
    prepare-code-coverage-artifact.py script from LLVM utils
    """

    stats_file_name = "summary.txt"

    def get_tool_name(self):
        return "LLVM"

    def read_from_str(self, s: str) -> Optional[dict]:
        """
        Parse data previously read from summary.txt file.
        Return coverage stats.
        Expected data format:
        ```
        Filename                      Regions    Missed Regions     Cover   Functions  Missed Functions  Executed       Lines      Missed Lines     Cover    Branches   Missed Branches     Cover
        -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        include/funcs.h                     3                 2    33.33%           3                 2    33.33%           9                 6    33.33%           0                 0         -
        src/fuzzable_app.cpp               33                 6    81.82%           3                 0   100.00%          71                14    80.28%          26                 6    76.92%
        -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        TOTAL                              36                 8    77.78%           6                 2    66.67%          80                20    75.00%          26                 6    76.92%
        ```
        """

        cov_data = s.split("\n")
        cov_data = list(filter(lambda line: len(line) > 0, cov_data))

        self._check_data_headers(cov_data[0])

        totals = cov_data[-1]
        if not totals.startswith("TOTAL"):
            raise LLVMSummaryCoverageStatsError("last line doesn't start with 'TOTAL'")

        return self._totals_to_dict(totals)

    def _check_data_headers(self, got_headers: str):
        expected_headers = [
            "Filename",
            "Regions",
            "Missed Regions",
            "Cover",
            "Functions",
            "Missed Functions",
            "Executed",
            "Lines",
            "Missed Lines",
            "Cover",
            "Branches",
            "Missed Branches",
            "Cover",
        ]

        expected_merged_header = squeeze_spaces(" ".join(expected_headers)).lower()
        got_header = squeeze_spaces(got_headers).lower()

        if expected_merged_header != got_header:
            raise LLVMSummaryCoverageStatsError("headers mismatch")

    def _totals_to_dict(self, totals: str) -> dict:
        cov_stats = re.split(r"\s+", totals)[1:]

        num_values = len(cov_stats)
        if num_values != 12:
            raise LLVMSummaryCoverageStatsError(
                f"in TOTAL line: expected 12 values, but got {num_values}"
            )

        # skip region coverage info
        cov_stats = cov_stats[3:]

        keys = [
            "func_cover",
            "func_total",
            "line_cover",
            "line_total",
            "bb_cover",
            "bb_total",
        ]

        result = {}

        for i in range(3):
            total, miss = cov_stats[i * 3 :][:2]
            cov = int(total) - int(miss)
            result[keys[i * 2]] = cov
            result[keys[i * 2 + 1]] = int(total)

        return result
