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
from dataclasses import dataclass

import os
import json
import logging

log = logging.getLogger(__name__)

from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory
from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats

from bugbane.modules.stats.coverage.factory import CoverageStatsFactory
from bugbane.modules.stats.coverage.coverage_stats import CoverageStats

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo

from bugbane.modules.file_utils import (
    none_on_bad_nonempty_dir,
    none_on_bad_nonempty_file,
)

from bugbane.modules.format import (
    count_to_report_count_cyr,
    count_to_report_count_with_unit_cyr,
    seconds_to_report_duration_cyr,
)


class FuzzDataError(Exception):
    """Custom exception type for errors in FuzzDataSuite class"""


@dataclass
class FuzzDataSuite:
    """
    Holds paths to fuzzing result files
    """

    build_log_path: Optional[str] = None
    build_cmds_path: Optional[str] = None
    fuzz_cmds_path: Optional[str] = None
    coverage_report_path: Optional[str] = None  # path to html
    in_dir: Optional[str] = None
    out_dir: Optional[str] = None
    dicts_dir: Optional[str] = None  # dict files are found by *.dict mask
    screen_dumps_dir: Optional[str] = None  # path to tmux capture-pane results
    vars_json_path: Optional[str] = None

    def __post_init__(self):
        self.coverage_stats: Optional[CoverageStats] = None
        self.fuzz_stats: Optional[FuzzStats] = None

    def set_coverage_stats(self, stats: CoverageStats):
        """
        Sets instance variable self.coverage_stats to stats
        """
        self.coverage_stats = stats

    def set_fuzz_stats(self, stats: FuzzStats):
        """
        Sets instance variable self.fuzz_stats to stats
        """
        self.fuzz_stats = stats

    @classmethod
    def unpack_from_fuzzing_suite_dir(cls, path: str):
        """
        Return tuple: (FuzzDataSuite, bane_vars_dict)
        """
        suite = cls.from_fuzzing_suite_dir(path)
        return (suite, suite.load_vars())

    @classmethod
    def from_fuzzing_suite_dir(cls, path: str):
        """
        Instantiate FuzzDataSuite objects
        Fill paths from given directory,
        nonexisting files and dirs will get values of None

        This structure is expected:
        path/
            bugbane.json
            build.cmds
            build.log
            fuzz.cmds
            in/
                <samplename>
                ...
            out/
                <fuzzername>/
                    crashes/
                    hangs/
                    queue/
                    cmdline
                    fuzz_stats
                ...
            dicts/
                <dictname>.dict
                ...
            coverage_report/
                index.html
                ...
            screens/
                screen0: fuzz stats
                screen1-N: fuzzer screens
        """

        if not os.path.isdir(path):
            raise FuzzDataError(f"no such directory: '{path}'")

        if not os.listdir(path):
            raise FuzzDataError(f"directory is empty: '{path}'")

        build_cmds_path = none_on_bad_nonempty_file(path, "build.cmds")
        build_log_path = none_on_bad_nonempty_file(path, "build.log")
        fuzz_cmds_path = none_on_bad_nonempty_file(path, "fuzz.cmds")
        coverage_report_path = none_on_bad_nonempty_dir(path, "coverage_report")
        in_dir = none_on_bad_nonempty_dir(path, "in")
        out_dir = none_on_bad_nonempty_dir(path, "out")
        dicts_dir = none_on_bad_nonempty_dir(path, "dicts")
        screen_dumps_dir = none_on_bad_nonempty_dir(path, "screens")
        vars_json_path = none_on_bad_nonempty_file(path, "bugbane.json")

        return cls(
            build_log_path=build_log_path,
            build_cmds_path=build_cmds_path,
            fuzz_cmds_path=fuzz_cmds_path,
            coverage_report_path=coverage_report_path,
            in_dir=in_dir,
            out_dir=out_dir,
            dicts_dir=dicts_dir,
            screen_dumps_dir=screen_dumps_dir,
            vars_json_path=vars_json_path,
        )

    def to_data_dict(self) -> dict:
        data = self.load_vars()
        self._loaded_vars_should_present(data)
        data.update(self._load_data_from_files())

        data["fuzz_cores_with_units"] = count_to_report_count_with_unit_cyr(
            data["fuzz_cores"], "on_cores"
        )
        data["fuzz_time_real_with_units"] = seconds_to_report_duration_cyr(
            data["fuzz_time_real_seconds"]
        )
        return data

    def load_vars(self) -> dict:
        """Loads and returns variables from JSON file"""
        if self.vars_json_path is None:
            raise FuzzDataError("no json file in fuzzing data suite")

        try:
            with open(self.vars_json_path, "rt") as json_file:
                data = json.load(json_file)
        except OSError as e:
            raise FuzzDataError(
                f"while trying to load json file '{self.vars_json_path}': {e}"
            ) from e
        try:
            vars = data["fuzzing"]
        except KeyError:
            FuzzDataError(
                f"while trying to load json file '{self.vars_json_path}': no 'fuzzing' dictionary in file"
            )
        return vars

    def save_vars(self, bane_vars: dict):
        """
        Save new bane_vars to JSON file
        """
        if self.vars_json_path is None:
            raise FuzzDataError(
                "no json file in fuzzing data suite, don't know where to save new vars"
            )

        data = {"fuzzing": bane_vars}
        try:
            with open(self.vars_json_path, "wt") as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)
        except OSError as e:
            raise FuzzDataError(
                f"while trying to save json file '{self.vars_json_path}': {e}"
            ) from e

    def _loaded_vars_should_present(self, d: dict):
        """
        Raise FuzzDataError if some necessary data is missing in input dict
        """

        expected_vars = [
            "application_name",
            "fuzz_cores",
            "builder_type",
            "fuzzer_type",
            "is_library",
            "is_open_source",
            "language",
            "module_name",
            "os_name",
            "os_version",
            "parse_format",
            "product_name",
            "product_version",
            "tested_source_file",
            "tested_source_function",
        ]

        not_found = [k for k in expected_vars if k not in d]

        if not_found:
            raise FuzzDataError(
                f"variables not defined in input fuzzing suite: {', '.join(not_found)}"
            )

    def _load_data_from_files(self) -> dict:
        """
        Loads all the text data in fuzzing suite and returns it as dict
        """
        result = {}
        self._add_loadables_to_dict(result)
        self._add_fuzz_stats_to_dict(result)
        self._add_cov_stats_to_dict(result)
        return result

    def _add_loadables_to_dict(self, result: dict):
        """
        Adds text content read from files to input dict without any processing
        """

        loadables = {
            "build_cmds": self.build_cmds_path,
            "fuzz_cmds": self.fuzz_cmds_path,
        }

        for key, path in loadables.items():
            contents = self._load_file_contents(path)
            if contents is None:
                continue
            result[key] = contents.rstrip("\n")

    def _load_file_contents(self, path: Optional[str]) -> Optional[str]:
        if path is None:
            return None

        try:
            with open(path, "rt") as f:
                contents = f.read()
        except OSError as e:
            raise FuzzDataError(
                f"while trying to load contents from file '{path}': {e}"
            ) from e

        return contents

    def _add_fuzz_stats_to_dict(self, result: dict):
        """
        Get fuzzer statistics from fuzzer_stats, etc
        """
        if self.fuzz_stats is None:
            raise FuzzDataError("fuzzer stats not set")

        if not self.out_dir:
            return

        try:
            fuzzer_info: FuzzerInfo = FuzzerInfoFactory.create(
                self.fuzz_stats.fuzzer_type()
            )
        except TypeError as e:
            raise FuzzDataError(
                f"wasn't able to create fuzzer paths object: {e}"
            ) from e

        self.fuzz_stats.load(fuzzer_info.stats_dir(self.out_dir))
        log.debug("Loaded FuzzStats stats: %s", self.fuzz_stats)

        # TODO: move all formatting to emitter
        result["execs_total"] = count_to_report_count_cyr(self.fuzz_stats.execs)
        result["execs_total_with_units"] = count_to_report_count_with_unit_cyr(
            self.fuzz_stats.execs, "execs"
        )

        result["num_crashes"] = count_to_report_count_cyr(self.fuzz_stats.crashes)
        result["num_crashes_with_units"] = count_to_report_count_with_unit_cyr(
            self.fuzz_stats.crashes, "crashes"
        )

        result["num_hangs"] = count_to_report_count_cyr(self.fuzz_stats.hangs)
        result["num_hangs_with_units"] = count_to_report_count_with_unit_cyr(
            self.fuzz_stats.hangs, "hangs"
        )

    def _add_cov_stats_to_dict(self, result: dict):
        """
        Get coverage info from index.html, summary.txt, etc.
        """

        if self.coverage_stats is None:
            raise FuzzDataError("coverage stats not set")

        if not self.coverage_report_path:
            return

        self.coverage_stats.load(self.coverage_report_path)
        log.debug("Loaded CoverageStats: %s", self.coverage_stats)

        result["cov_bb"] = self.coverage_stats.bb_cover_percent
        result["cov_func"] = self.coverage_stats.func_cover_percent
        result["cov_line"] = self.coverage_stats.line_cover_percent
        result["coverage_tools"] = [self.coverage_stats.get_tool_name()]
