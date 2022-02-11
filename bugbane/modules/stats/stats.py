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
from abc import ABC, abstractmethod

import os
import glob
import logging

from bugbane.modules.string_utils import is_glob_mask

log = logging.getLogger(__name__)

from bugbane.modules.file_utils import none_on_bad_nonempty_file


class StatsError(Exception):
    """Base class for exceptions happened during work with stats"""


class Stats(ABC):
    stats_file_name: Optional[str] = None

    @abstractmethod
    def clear(self):
        """Clears all the stats data"""

    @abstractmethod
    def to_dict(self) -> dict:
        """Represents all the stats data as dictionary"""

    def load(self, dir_path: str):
        """
        Template method.
        Loads data from directory
        """

        self.clear()
        stats = {}

        if is_glob_mask(self.stats_file_name):
            mask = os.path.join(dir_path, self.stats_file_name)
            paths = glob.glob(mask)
            for path in paths:
                stats_dict = self.read_one(path)
                if stats_dict is not None:
                    stats[path] = stats_dict
        else:
            single_report_path = none_on_bad_nonempty_file(
                dir_path, self.stats_file_name
            )
            if single_report_path is not None:
                stats_dict = self.read_one(single_report_path)
                if stats_dict is not None:
                    stats["."] = stats_dict

            stats.update(self._read_all(dir_path))

        self._load_multidict(stats)
        log.verbose3("Loaded %d stats from directory %s", len(stats), dir_path)
        self._ensure_format()

    def _read_all(self, dir_path: str) -> dict:
        """
        Template method.
        Returns dict of dicts with stats.
        Top level dict key is application name (directory part), value is stats of one entity (dict).
        Returned dict is only meaningful for concrete Stats class.
        """
        result = {}
        dirs = [os.path.join(dir_path, d) for d in os.listdir(dir_path)]
        subdirs = sorted((d for d in dirs if os.path.isdir(d)))
        log.debug(
            "loading stats from directory '%s' (%d subdirs)",
            dir_path,
            len(subdirs),
        )

        for subdir in subdirs:
            file_path = none_on_bad_nonempty_file(subdir, self.stats_file_name)

            if file_path is None:
                continue

            stats = self.read_one(file_path)
            if stats is None:
                continue

            result[subdir] = stats

        return result

    @abstractmethod
    def read_one(self, file_path: str) -> Optional[dict]:
        """
        Read one stats file,
        return dictionary with stats data
        (meaningful for concrete Stats class).
        Return None if stats should be discarded.
        """

    @abstractmethod
    def _load_multidict(self, data: dict):
        """
        Walk over keys & values in data dictionary, where each key is subdir name
        and each value represents stats loaded from one stats file in corresponding subdir.
        Save stats from dictionary to instance variables.
        Input dictionary (returned by self._read_all) is only meaningful for concrete Stats class
        """

    @abstractmethod
    def _ensure_format(self):
        """
        Fix string integers, round floats to specific number of digits, etc.
        """
