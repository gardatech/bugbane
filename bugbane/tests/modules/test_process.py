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

from typing import Tuple, List, Dict, Optional

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
