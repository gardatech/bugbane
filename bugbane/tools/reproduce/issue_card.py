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

import re
import logging

log = logging.getLogger(__name__)

from .verdict import Verdict

from .trace_utils import (
    anonymize_run_string,
    get_crash_location,
    get_hang_location,
    location_to_file_line,
    remove_column_from_location,
)


@dataclass
class IssueCard:
    reproduce_cmd: Optional[str] = None
    reproduce_env: Optional[str] = None
    output: Optional[str] = None
    binary: Optional[str] = None
    sample: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    verdict: Optional[Verdict] = None
    title: Optional[str] = None

    def load_location_and_set_title(self, src_path: Optional[str] = None):
        if self.verdict == Verdict.HANG:
            location = get_hang_location(self.output, src_path)
        else:
            location = get_crash_location(self.output, src_path)

        title = self.verdict.description

        if location is None:
            log.warning(
                "wasn't able to extract crash or hang location (binary: %s, sample: %s)",
                self.binary,
                self.sample,
            )
        else:
            location = remove_column_from_location(location)
            title += " " + location

        title = anonymize_run_string(title)
        self.title = title

        file, line = location_to_file_line(location)
        self.file = file
        self.line = line

    def issue_card_to_hashable_str(self) -> str:
        """Generalizes output and verdict to hashable string"""

        if not self.output:
            return f"verdict={self.verdict.name},output={self.output}"

        t = anonymize_run_string(self.output)

        if "SUMMARY: UndefinedBehaviorSanitizer" not in self.output:
            return f"verdict={self.verdict.name},output={t}"

        re_distinct_number = re.compile(r"(?:^|\s+)+([+-]?\d+)(?:$|\s+)")
        re_runtime_error = re.compile(r"^(.*:\s*runtime error:\s*.*)$", re.MULTILINE)

        runtime_error_match = re.match(re_runtime_error, t)
        if runtime_error_match:
            t = runtime_error_match.group(1)
            t = re.sub(re_distinct_number, " <NUMBER> ", t)
            t = "UndefinedBehaviorSanitizer: " + t

        return f"verdict={self.verdict.name},output={t}"
