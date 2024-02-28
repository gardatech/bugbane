# Copyright 2022-2024 Garda Technologies, LLC. All rights reserved.
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

import pytest

from bugbane.tools.reproduce.bugsamplesaver import BugSampleSaver, BugSampleSaverError


@pytest.mark.parametrize(
    "issue_title, sample_file_name",
    [
        (
            "Crash in LibName::Method at /opt/libname/src/parse.cpp:432",
            "crash_in_libname_method_at_opt_libname_src_parse_cpp_432",
        ),
    ],
)
def test_title_to_sample_name(issue_title: str, sample_file_name: str) -> None:
    bss = BugSampleSaver(max_file_name_len=255)
    assert bss.title_to_sample_name(issue_title) == sample_file_name


def test_file_len_limit_too_low() -> None:
    with pytest.raises(BugSampleSaverError):
        BugSampleSaver(max_file_name_len=14)
