# Copyright 2022-2025 Garda Technologies, LLC. All rights reserved.
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

from typing import Dict, Optional

import pytest

import bugbane.modules.process as p


@pytest.mark.parametrize(
    "env_cmd, cmd",
    [
        ("", ""),
        ("a", "a"),
        ("env", "env"),
        ("./env", "./env"),
        ("./env ", "./env "),
        ("./app @@", "./app @@"),
        ("env env", "env"),
        ("env A=1 ./env", "./env"),
        ("env a", "a"),
        ("env A=1 a", "a"),
        ("env Abc=123 DEFGH=1=2 ./app", "./app"),
        ("env AFL_PRELOAD=/path/to/something.so ./myapp --fuzz", "./myapp --fuzz"),
    ],
)
def test_remove_prefix_env(env_cmd: str, cmd: str) -> None:
    assert p.remove_prefix_env(env_cmd) == cmd


@pytest.mark.parametrize(
    "env_str, env_dict",
    [
        (None, {}),
        ("a=1", {"a": "1"}),
        ("a=1 bcd=efg", {"a": "1", "bcd": "efg"}),
    ],
)
def test_make_env_shell_str(env_str: Optional[str], env_dict: Dict[str, str]) -> None:
    assert p.make_env_shell_str(env_dict) == env_str


@pytest.mark.parametrize(
    "env_str, env_dict",
    [
        (None, {}),
        ("a=1", {"a": "1"}),
        ("a=1 bcd=efg", {"a": "1", "bcd": "efg"}),
    ],
)
def test_make_env_dict_from_str(
    env_str: Optional[str], env_dict: Dict[str, str]
) -> None:
    assert p.make_env_dict_from_str(env_str) == env_dict


def test_make_env_dict_from_str_raises() -> None:
    with pytest.raises(p.ProcessException):
        p.make_env_dict_from_str("A")
