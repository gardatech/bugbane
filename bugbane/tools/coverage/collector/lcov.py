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

import logging

log = logging.getLogger(__name__)

from bugbane.modules.process import checked_run_shell_cmd

from .collector import CoverageCollector, CoverageCollectorError
from .factory import CoverageCollectorFactory


@CoverageCollectorFactory.register("lcov")
class LCOVCoverageCollector(CoverageCollector):
    """
    Class suitable for collecting coverage using lcov (uses gcov) and genhtml
    """

    def cleanup_coverage_info(self):
        """
        Recursively remove gcda files in self.cov_files_path
        """
        cmd = f"lcov -z -d {self.cov_files_path}"
        if not checked_run_shell_cmd(cmd):
            raise CoverageCollectorError("lcov -z run failed")

    def generate_report(self, report_dir: str, include_source: bool = True):
        """
        Capture coverage info from gcda & gcno files, generate HTML report
        """
        cmd = self._make_lcov_capture_cmd()

        if not checked_run_shell_cmd(cmd, timeout_sec=60 * 60):
            raise CoverageCollectorError("lcov -c run failed")

        cmd = (
            f"genhtml -o {report_dir} --ignore-errors source --branch-coverage cov.info"
        )
        if not include_source:
            cmd += " --no-source"

        if not checked_run_shell_cmd(cmd):
            raise CoverageCollectorError("genhtml run failed")

    def _make_lcov_capture_cmd(self):
        """
        Generate lcov --capture command
        """
        cmd = f"lcov -b {self.cov_files_path} -d {self.cov_files_path}"
        cmd += " --no-external --rc lcov_branch_coverage=1 --capture -o cov.info"
        return cmd
