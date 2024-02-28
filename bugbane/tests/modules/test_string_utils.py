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

from copy import copy

import pytest

from bugbane.modules import string_utils


def test_is_glob_mask():
    assert string_utils.is_glob_mask("*")
    assert string_utils.is_glob_mask("?")
    assert string_utils.is_glob_mask("out/*/queue/id*")

    assert not string_utils.is_glob_mask("out/m1/fuzzer_stats")
    assert not string_utils.is_glob_mask("")


def test_replace_part_in_str_list():
    cmds = [
        "./basic/app --arg $arg @@",
        "./asan/app --arg $arg @@",
        "./ubsan/app --arg $arg @@",
    ]
    expected = [
        "./basic/app --arg runtime @@",
        "./asan/app --arg runtime @@",
        "./ubsan/app --arg runtime @@",
    ]
    last = len(cmds) - 1
    cmds_copy = copy(cmds)
    string_utils.replace_part_in_str_list(cmds_copy, "$arg", "runtime", -1, 0, last)
    print(cmds_copy)
    assert cmds_copy == expected


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
def test_shorten_string(
    long_name: str, mid_part: str, max_len: int, shortened: str
) -> None:
    assert (
        string_utils.shorten_string(long_name, new_mid_part=mid_part, max_len=max_len)
        == shortened
    )
