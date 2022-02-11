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

from typing import Dict, Optional, Union
from abc import abstractmethod
from dataclasses import dataclass

import logging

log = logging.getLogger(__name__)

from ..stats import Stats, StatsError


class CoverageStatsError(StatsError):
    """Exceptions that happen in CoverageStats class"""


@dataclass
class CoverageStats(Stats):
    num_reports: int = 0
    bb_total: Optional[int] = None
    bb_cover: Optional[int] = None
    line_total: Optional[int] = None
    line_cover: Optional[int] = None
    func_total: Optional[int] = None
    func_cover: Optional[int] = None

    def clear(self):
        self.num_reports = 0
        self.bb_total = None
        self.bb_cover = None
        self.line_total = None
        self.line_cover = None
        self.func_total = None
        self.func_cover = None

    @property
    def bb_cover_percent(self) -> Optional[float]:
        return self._get_cover_percent(self.bb_cover, self.bb_total)

    @property
    def line_cover_percent(self) -> Optional[float]:
        return self._get_cover_percent(self.line_cover, self.line_total)

    @property
    def func_cover_percent(self) -> Optional[float]:
        return self._get_cover_percent(self.func_cover, self.func_total)

    def _get_cover_percent(
        self, cover: Optional[int], total: Optional[int]
    ) -> Optional[float]:
        if cover is None or total is None:
            return None

        if total == 0:
            return 100.0

        if cover == 0:
            return 0.0

        percent = 100.0 * (cover / total)
        if percent > 100.0:
            percent = 100.0

        return round(percent, 2)

    def to_dict(self) -> Dict[str, Optional[Union[int, float]]]:
        self._ensure_format()
        return {
            "bb_cover": self.bb_cover,
            "bb_total": self.bb_total,
            "bb_cover_percent": self.bb_cover_percent,
            "line_cover": self.line_cover,
            "line_total": self.line_total,
            "line_cover_percent": self.line_cover_percent,
            "func_cover": self.func_cover,
            "func_total": self.func_total,
            "func_cover_percent": self.func_cover_percent,
        }

    def _ensure_format(self):
        if self.bb_cover_percent is not None:
            self.bb_cover = int(self.bb_cover)
            self.bb_total = int(self.bb_total)
        if self.line_cover_percent is not None:
            self.line_cover = int(self.line_cover)
            self.line_total = int(self.line_total)
        if self.func_cover_percent is not None:
            self.func_cover = int(self.func_cover)
            self.func_total = int(self.func_total)

    def add_stats_from(self, *others):
        """
        *others: iterable of CoverageStats
        """

        func_cov = [self.func_cover]
        func_total = [self.func_total]
        line_cov = [self.line_cover]
        line_total = [self.line_total]
        bb_cov = [self.bb_cover]
        bb_total = [self.bb_total]

        for other in others:
            self.num_reports += 1
            func_cov.append(other.func_cover)
            func_total.append(other.func_total)

            line_cov.append(other.line_cover)
            line_total.append(other.line_total)

            bb_cov.append(other.bb_cover)
            bb_total.append(other.bb_total)

        func_cov, func_total, line_cov, line_total, bb_cov, bb_total = (
            list(filter(lambda v: v is not None, cov))
            for cov in (func_cov, func_total, line_cov, line_total, bb_cov, bb_total)
        )
        if func_cov and func_total:
            self.func_cover = sum(func_cov)
            self.func_total = sum(func_total)

        if line_cov and line_total:
            self.line_cover = sum(line_cov)
            self.line_total = sum(line_total)

        if bb_cov and bb_total:
            self.bb_cover = sum(bb_cov)
            self.bb_total = sum(bb_total)

    def _load_multidict(self, data: dict):
        # TODO: convert dict to CoverageStats and use self.add_stats_from
        func_cov = [self.func_cover]
        func_total = [self.func_total]
        line_cov = [self.line_cover]
        line_total = [self.line_total]
        bb_cov = [self.bb_cover]
        bb_total = [self.bb_total]

        for subdir, cov_stats in data.items():
            self.num_reports += 1

            func_cov.append(cov_stats.get("func_cover", None))
            func_total.append(cov_stats.get("func_total", None))

            line_cov.append(cov_stats.get("line_cover", None))
            line_total.append(cov_stats.get("line_total", None))

            bb_cov.append(cov_stats.get("bb_cover", None))
            bb_total.append(cov_stats.get("bb_total", None))

            log.verbose3("Loaded coverage stats from subdir %s", subdir)

        func_cov, func_total, line_cov, line_total, bb_cov, bb_total = (
            list(filter(lambda v: v is not None, cov))
            for cov in (func_cov, func_total, line_cov, line_total, bb_cov, bb_total)
        )
        if func_cov and func_total:
            self.func_cover = sum(func_cov)
            self.func_total = sum(func_total)

        if line_cov and line_total:
            self.line_cover = sum(line_cov)
            self.line_total = sum(line_total)

        if bb_cov and bb_total:
            self.bb_cover = sum(bb_cov)
            self.bb_total = sum(bb_total)

    @abstractmethod
    def get_tool_name(self):
        """
        Return coverage tool name
        examples: 'lcov, genhtml' or 'LLVM' or 'Coverage.py'
        """

    def read_one(self, file_path) -> Optional[dict]:
        """
        Read coverage file.
        Return coverage stats
        """
        try:
            with open(file_path, "rt", encoding="utf-8") as f:
                cov_data = f.read()
            stats = self.read_from_str(cov_data)
        except OSError as e:
            raise CoverageStatsError(
                f"wasn't able to read file '{file_path}': {e}"
            ) from e
        except (IndexError, ValueError) as e:
            raise CoverageStatsError(
                f"bad data format in file '{file_path}': {e}"
            ) from e
        return stats

    @abstractmethod
    def read_from_str(self, s: str) -> Optional[dict]:
        """
        Read coverage information from string (read from file)
        """
