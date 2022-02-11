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

from typing import List, Optional

import os
import re
import shutil

from bs4 import BeautifulSoup

import logging

log = logging.getLogger(__name__)

from bugbane.modules.process import checked_run_shell_cmd
from bugbane.modules.file_utils import none_on_bad_nonempty_file

from .collector import CoverageCollector, CoverageCollectorError
from .factory import CoverageCollectorFactory


@CoverageCollectorFactory.register("go-tool-cover")
class GoCoverageCollector(CoverageCollector):
    """
    Class suitable for collecting coverage using "go tool cover"
    """

    def collect(self):
        """
        Custom implementation of parent class method 'collect' for golang
        """
        self.cleanup_coverage_info()
        self._process_coverage_info()

    def cleanup_coverage_info(self):
        """
        Remove "coverprofile" in self.cov_files_path
        """
        log.verbose2("Cleaning existing (processed) coverage data")

        file_path = none_on_bad_nonempty_file(self._get_processed_cov_file_name())
        if file_path is None:
            return

        try:
            os.remove(file_path)
        except OSError as e:
            raise CoverageCollectorError(
                f"couldn't delete coverage file {file_path}"
            ) from e

    def _process_coverage_info(self):
        """
        Sanitize and filter coverage file before generating report
        """
        lines = self._read_cov_file()
        sanitized = self._sanitize_cov_file_lines(lines)
        filtered = self._filter_cov_file_lines(sanitized)
        self._write_cov_file(filtered)

    def _read_cov_file(self) -> List[str]:
        """
        Read lines from coverage file
        """
        file_path = self._get_coverage_file_name()
        checked_file_path = none_on_bad_nonempty_file(file_path)
        if checked_file_path is None:
            raise CoverageCollectorError(
                f"file doesn't exist, empty or not readable: {file_path}"
            )

        try:
            with open(checked_file_path, "rt", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            raise CoverageCollectorError(
                f"couldn't read coverage file {checked_file_path}"
            ) from e

        return lines

    def _get_coverage_file_name(self):
        return os.path.join(self.cov_files_path, "coverprofile")

    def _sanitize_cov_file_lines(self, lines: List[str]) -> List[str]:
        """
        Remove bad coverage lines inserted by go-fuzz
        """
        lines = [line for line in lines if "0.0,1.1" not in line]
        return lines

    def _filter_cov_file_lines(self, lines: List[str]) -> List[str]:
        """
        Remove coverage lines not starting with self.src_root
        """
        if not self.src_root:
            return lines

        filtered_lines = [
            line
            for line in lines
            if not (line.startswith("/") and not line.startswith(self.src_root))
        ]
        return filtered_lines

    def _write_cov_file(self, lines: List[str]):
        """Save lines as processed coverage file"""
        file_path = self._get_processed_cov_file_name()
        try:
            with open(file_path, "wt", encoding="utf-8") as f:
                f.writelines(lines)
        except OSError as e:
            raise CoverageCollectorError(
                f"couldn't write coverage file {file_path}"
            ) from e

    def _get_processed_cov_file_name(self):
        return self._get_coverage_file_name() + ".processed"

    def generate_report(self, report_dir: str, include_source: bool = True):
        """
        Collect coverage data from processed coverage profile file.
        Generate HTML report and summary.txt report suitable for parsing total coverage percent.
        """

        try:
            os.makedirs(report_dir, exist_ok=True)
        except OSError as e:
            raise CoverageCollectorError(
                f"wasn't able to create coverage report dir {report_dir}"
            ) from e

        reports = {"html": "index.html", "func": "summary.txt"}
        proc_file_name = self._get_processed_cov_file_name()

        for arg, file_name in reports.items():
            report_file = os.path.join(report_dir, file_name)
            cmd = f"go tool cover -{arg}={proc_file_name} -o {report_file}"

            if not checked_run_shell_cmd(cmd):
                raise CoverageCollectorError(f"go tool cover failed, cmd was {cmd}")

        html_file_path = os.path.join(report_dir, reports["html"])
        success = self._post_process_html_file(html_file_path)
        log.verbose1("HTML post processing %s", "succeeded" if success else "failed")

    def _post_process_html_file(self, html_path: str) -> bool:
        """
        Try to edit colors in resulting HTML file and
        save original HTML file as <name>.original.html.
        Return False on fail, True on success
        """
        try:
            with open(html_path, "rt", encoding="utf-8") as f:
                html = f.read()
        except OSError as e:
            log.error(
                "HTML post process: failed to read HTML from file %s. Message: %s",
                html_path,
                e,
            )
            return False

        new_html = self._post_process_html_string(html)
        if not new_html:
            return False

        orig_name = html_path + ".original.html"
        try:
            os.rename(html_path, orig_name)
        except OSError as e:
            log.error(
                "HTML post process: failed to rename %s to %s. Message: %s",
                html_path,
                orig_name,
                e,
            )
            return False

        try:
            with open(html_path, "wt", encoding="utf-8") as f:
                f.write(new_html)
        except OSError as e:  # rename back, dest file may exist
            log.error(
                "HTML post process: failed to write processed HTML to file %s. Message: %s",
                html_path,
                e,
            )
            shutil.copy(orig_name, html_path)
            os.remove(orig_name)
            return False

        return True

    def _post_process_html_string(self, html: str) -> Optional[str]:
        """
        Edit colors (background: black -> white, text: green -> black)
        """
        soup = BeautifulSoup(html, "lxml")
        style = soup.find("style")
        if not style:
            log.trace("style element not found")
            return None

        new_style = str(style.text)
        new_style = new_style.replace("background: black;", "background: white;")

        re_cov_color = re.compile(r"color: rgb\(\s*\d+\s*,\s*(?!0+)\d+\s*,\s*\d+\s*\)")
        new_style = re_cov_color.sub("color: rgb(0, 0, 0)", new_style)

        style.string = new_style

        return str(soup)
