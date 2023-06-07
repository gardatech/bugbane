# Copyright 2022-2023 Garda Technologies, LLC. All rights reserved.
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

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bs4 import BeautifulSoup

from .coverage_stats import CoverageStats, CoverageStatsError
from .factory import CoverageStatsFactory


class LCOVCoverageStatsError(CoverageStatsError):
    """Exceptions that happen in LCOVCoverageStats class"""


@CoverageStatsFactory.register("lcov")
@CoverageStatsFactory.register("lcov-llvm")
class LCOVCoverageStats(CoverageStats):
    """Collects coverage information from HTML report, generated by lcov + genhtml"""

    stats_file_name = "index.html"

    def get_tool_name(self):
        return "lcov, genhtml"

    def read_from_str(self, s: str) -> Optional[dict]:
        """
        Parse data previously read from coverage stats file.
        Return coverage stats.
        Expected format:
        ```
        <tr>
            <td class="headerItem">Test:</td>
            <td class="headerValue">cov.info</td>
            <td></td>
            <td class="headerItem">Lines:</td>
            <td class="headerCovTableEntry">1942</td>
            <td class="headerCovTableEntry">7073</td>
            <td class="headerCovTableEntryLo">27.5 %</td>
          </tr>
          <tr>
            <td class="headerItem">Date:</td>
            <td class="headerValue">2021-12-08 15:17:02</td>
            <td></td>
            <td class="headerItem">Functions:</td>
            <td class="headerCovTableEntry">387</td>
            <td class="headerCovTableEntry">809</td>
            <td class="headerCovTableEntryLo">47.8 %</td>
          </tr>
          <tr>
            <td></td>
            <td></td>
            <td></td>
            <td class="headerItem">Branches:</td>
            <td class="headerCovTableEntry">941</td>
            <td class="headerCovTableEntry">7260</td>
            <td class="headerCovTableEntryLo">13.0 %</td>
          </tr>
        ```
        """

        if "LCOV - code coverage report" not in s:
            raise LCOVCoverageStatsError("LCOV header not found")

        if '">top level</a>' in s:  # not top level page
            return None

        mapping = {
            "Lines:": ("line_cover", "line_total"),
            "Functions:": ("func_cover", "func_total"),
            "Branches:": ("bb_cover", "bb_total"),
        }

        totals = {}

        soup = BeautifulSoup(s, "lxml")
        for cov_stat_text, keys in mapping.items():
            item = soup.find(class_="headerItem", string=cov_stat_text)
            if item is None:
                totals[keys[0]] = None
                totals[keys[1]] = None
                continue

            hit = item.find_next_sibling()
            if hit is None:
                raise LCOVCoverageStatsError(
                    "unknown HTML format (hit count not found)"
                )

            total = hit.find_next_sibling()
            if total is None:
                raise LCOVCoverageStatsError(
                    "unknown HTML format (total count not found)"
                )

            totals[keys[0]] = int(hit.text.strip())
            totals[keys[1]] = int(total.text.strip())

        return totals
