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
    tested_func = string_utils.replace_part_in_str_list

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
    tested_func(cmds_copy, "$arg", "runtime", -1, 0, last)
    print(cmds_copy)
    assert cmds_copy == expected
