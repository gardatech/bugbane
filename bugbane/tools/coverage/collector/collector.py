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

from typing import Dict, List, Optional
from abc import ABC, abstractmethod

from bugbane.modules.process import prepare_run_args_for_shell, run_shell_cmd

import glob
import logging

log = logging.getLogger(__name__)


class CoverageCollectorError(Exception):
    """Exception class for errors that happen during coverage collection"""


class CoverageCollector(ABC):
    def __init__(self):
        self.cov_files_path: Optional[str] = None
        self.masks: List[str] = []
        self.binary: Optional[str] = None
        self.run_args: Optional[List[str]] = None
        self.src_root: Optional[str] = None

    def assign_application(
        self,
        binary: str,
        run_args: Optional[List[str]] = None,
    ):
        """
        binary: path to coverage-instrumented build of tested application
        run_args: List[str] with run arguments and possibly @@
        """
        self.binary = binary
        self.run_args = run_args

    def assign_cov_files_path(self, cov_files_path: str):
        """
        cov_files_path: files, where coverage data will appear (gcda or profdata)

        for llvm cov_files_path is path to directory with profdata
        for lcov cov_files_path is path to src directory during build
        """
        self.cov_files_path = cov_files_path

    def assign_src_root(self, src_root: str):
        """
        src_root: path to source code from which tested application was built.

        May be used by subclasses for filtering coverage files to include in report
        """
        self.src_root = src_root

    def assign_sample_masks(self, masks: List[str]):
        self.masks = masks

    def collect(self):
        """
        Collect coverage information:
            this function should generate gcda or profdata files
            on filesystem.
        """
        log.verbose1("Cleaning existing coverage data")
        self.cleanup_coverage_info()
        self.run_all()

    def run_all(self):
        for sample in self.find_samples():
            self.run_one(sample)

    def find_samples(self) -> List[str]:
        samples = set()

        for mask in self.masks:
            samples.update(set(glob.glob(mask)))

        log.verbose1("Found %d samples", len(samples))

        return sorted(samples)

    def run_one(self, sample):
        """
        Run tested application on given sample
        """
        log.verbose3("Running sample %s", sample)

        cmd = self.binary
        cmd += " "
        cmd += prepare_run_args_for_shell(self.run_args, sample)

        run_shell_cmd(cmd, timeout_sec=20)

    @abstractmethod
    def cleanup_coverage_info(self):
        """
        Remove gcda or profdata files, etc.
        """

    @abstractmethod
    def generate_report(self, report_dir: str, include_source: bool = True):
        """
        Generate coverage report, be it HTML or something else.
        include_source: coverage report will contain source code, otherwise only coverage% data
        """
