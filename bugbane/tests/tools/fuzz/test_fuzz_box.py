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
from pytest_mock import MockerFixture

from bugbane.tools.fuzz.fuzz_box import limit_cpu_cores


def test_limit_cpu_cores(mocker: MockerFixture):
    default_for_empty = 8
    in_out = [
        # (from_config, --max-cpus, cpu_count), expected result
        ((None, 16, 4), 4),
        ((None, 16, 9), default_for_empty),
        ((1, 16, 4), 1),
        ((1, 16, 32), 1),
        ((1, 16, 1), 1),
        ((1, 1, 16), 1),
        ((2, 1, 16), 1),
        ((2, 16, 1), 1),
        ((2, 16, 16), 2),
        ((17, 16, 16), 16),
        ((100, 256, 512), 100),
    ]

    for (inp, expected) in in_out:
        from_config, max_cpus, cpu_count = inp
        mocker.patch("bugbane.tools.fuzz.fuzz_box.os.cpu_count", return_value=cpu_count)
        limited = limit_cpu_cores(from_config=from_config, max_from_args=max_cpus)
        assert limited == expected
