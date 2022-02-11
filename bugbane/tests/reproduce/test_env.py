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

import os
from unittest import mock

from bugbane.tools.reproduce.harvester import Harvester


@mock.patch.dict(
    os.environ, {"PATH": "/usr/bin:/bin", "ASAN_OPTIONS": "detect_leaks=0"}, clear=True
)
def test_set_run_env_append_asan_and_path():
    """
    ASAN_OPTIONS passed to set_run_env method, but also defined in env variables.
    User-defined env vars should be appended last
    """
    harvester = Harvester()
    harvester.set_run_env(
        {
            "UBSAN_OPTIONS": "print_stacktrace=1:allocator_may_return_null=1:detect_stack_use_after_return=1",
            "ASAN_OPTIONS": "allocator_may_return_null=1:detect_stack_use_after_return=1",
            "LANG": "C",
        }
    )
    run_env = harvester.run_env

    print(run_env)

    assert len(run_env) == 4

    assert (
        run_env["ASAN_OPTIONS"]
        == "allocator_may_return_null=1:detect_stack_use_after_return=1:detect_leaks=0"
    )
    assert run_env["PATH"] == "/usr/bin:/bin"


@mock.patch.dict(os.environ, {"ASAN_OPTIONS": "detect_leaks=0"}, clear=True)
def test_set_run_env_asan_in_env():
    """
    ASAN_OPTIONS not passed via set_run_env, but present in env variables
    """
    harvester = Harvester()
    harvester.set_run_env(
        {
            "UBSAN_OPTIONS": "print_stacktrace=1:allocator_may_return_null=1:detect_stack_use_after_return=1",
            "LANG": "C",
        }
    )
    run_env = harvester.run_env

    print(run_env)

    assert len(run_env) == 3

    assert run_env["ASAN_OPTIONS"] == "detect_leaks=0"
    assert "PATH" not in run_env
