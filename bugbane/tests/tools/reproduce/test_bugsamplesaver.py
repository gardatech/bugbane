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


@pytest.mark.parametrize(
    "long_name, mid_part, max_len, shortened",
    [
        ("12345", "*", 5, "12345"),
        ("12345", "**", 5, "12345"),
        ("12345", "*", 6, "12345"),
        ("12345", "**", 10, "12345"),
        ("12345", "*", 4, "12*5"),
        ("12345", "**", 4, "1**5"),
        ("12345", "*", 3, "1*5"),
        ("123456", "*", 3, "1*6"),
        ("123456", "*", 4, "12*6"),
        ("01234567890abcdefghijk", "_-_-_", 10, "012_-_-_jk"),
        ("01234567890abcdefghijk", "_-_-_", 11, "012_-_-_ijk"),
        ("01234567890abcdefghijkl", "_-_-_", 10, "012_-_-_kl"),
        ("01234567890abcdefghijkl", "_-_-_", 11, "012_-_-_jkl"),
    ],
)
def test_shorten_sample_name(
    long_name: str, mid_part: str, max_len: int, shortened: str
) -> None:
    assert (
        BugSampleSaver.shorten_sample_name(
            long_name, new_mid_part=mid_part, max_len=max_len
        )
        == shortened
    )
