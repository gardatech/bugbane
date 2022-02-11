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

import shlex
import pytest

from bugbane.tools.reproduce.main import Harvester
from bugbane.tools.reproduce.args import parse_args


@pytest.fixture(scope="session")
def harvester():
    argv = shlex.split(
        "bb-reproduce -vvvv --hang-timeout 1000 manual -o /mnt/dd.json --src-path /src --spec AFL++:/mnt/out/ ./basic:m1 ./asan:s14 ./ubsan:s15 ./cfisan:s16  -- ./basic"
    )
    args = parse_args(argv[1:])
    test_harvester = Harvester()

    test_harvester.set_run_args(args.program[1:])  # skip binary itself
    test_harvester.set_run_env(
        {
            "UBSAN_OPTIONS": "print_stacktrace=1:allocator_may_return_null=1:detect_stack_use_after_return=1",
            "ASAN_OPTIONS": "allocator_may_return_null=1:detect_stack_use_after_return=1",
            "LANG": "C",  # for GDB
        }
    )
    test_harvester.set_specs(args.spec)
    test_harvester.set_num_reruns(args.num_reruns)
    test_harvester.set_use_abspath(args.abspath)

    return test_harvester
