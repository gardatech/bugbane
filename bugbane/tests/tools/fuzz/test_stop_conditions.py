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

from typing import Dict, List

import pytest
from pytest_mock import MockerFixture

from unittest import mock
import os

from bugbane.modules.stats.fuzz.aflplusplus import AFLplusplusFuzzStats
from bugbane.tools.fuzz.stop_conditions import (
    check_if_stop_conditions_are_met,
    parse_fuzz_duration_triplet,
    StopConditionError,
    detect_required_stop_condition,
    explain_stop_conditions,
)

TIME_MOCK_PATH = "bugbane.tools.fuzz.stop_conditions.time"


@pytest.mark.parametrize(
    "duration_triplet, seconds_without_finds, fuzz_duration, exp_conditions_met",
    [
        # fmt: off
        # [min, w/o finds, max]
        ([200, 0, 0], 100, 199, {}),
        ([200, 0, 0], 100, 200, {"minutes_run_time": 3}),
        ([200, 0, 0], 100, 201, {"minutes_run_time": 3}),
        ([0, 120, 0], 119, 200, {}),
        ([0, 120, 0], 120, 200, {"minutes_without_paths": 2}),
        ([0, 120, 0], 121, 200, {"minutes_without_paths": 2}),
        ([0, 0, 240], 199, 199, {}),
        ([0, 0, 240], 199, 240, {"minutes_run_time": 4}),
        ([0, 0, 240], 199, 241, {"minutes_run_time": 4}),

        ([200, 120, 400], 120, 200, {"minutes_without_paths": 2}),
        ([200, 120, 400], 399, 401, {"minutes_without_paths": 2}),
        ([200, 100, 600],  99, 600, {"minutes_run_time": 10}),
        ([200, 100, 400],  99, 399, {}),
        ([200, 100,   0],  99, 200, {}),
        ([200, 120,   0], 120, 200, {"minutes_without_paths": 2}),
        ([  0, 100, 200],  99, 199, {}),
        ([  0, 180, 200], 180, 199, {"minutes_without_paths": 3}),
        ([  0, 100, 180],  99, 180, {"minutes_run_time": 3}),
        ([100,   0, 200], 100, 199, {}),
        ([100,   0, 180], 100, 180, {"minutes_run_time": 3}),
        ([380,   0, 200], 100, 379, {}),
        ([300,   0, 200], 100, 300, {"minutes_run_time": 5}),
        # fmt: on
    ],
)
def test_check_if_stop_conditions_are_met(
    mocker: MockerFixture,
    duration_triplet: List[int],
    seconds_without_finds: int,
    fuzz_duration: int,
    exp_conditions_met: Dict[str, int],
) -> None:
    fuzz_stats = AFLplusplusFuzzStats(
        start_timestamp=0, last_path_timestamp=fuzz_duration - seconds_without_finds
    )
    mocker.patch(TIME_MOCK_PATH, return_value=fuzz_duration)
    assert (
        check_if_stop_conditions_are_met(fuzz_stats, duration_triplet)
        == exp_conditions_met
    )


@pytest.mark.parametrize(
    "inp, exp",
    [
        # fmt: off
        ("0", [0, 0, 0]),
        ("-0", [0, 0, 0]),
        ("1", [0, 0, 1]),
        ("1:2:3", [1, 2, 3]),
        (":2:3", [0, 2, 3]),
        ("1:2:", [1, 2, 0]),
        (":123:", [0, 123, 0]),
        # fmt: on
    ],
)
def test_parse_fuzz_duration_triplet(inp: str, exp: List[int]) -> None:
    assert parse_fuzz_duration_triplet(inp) == exp


@pytest.mark.parametrize(
    "inp, exp",
    [
        # fmt: off
        ("1:0:3", [0, 0, 3]),
        ("3:0:3", [0, 0, 3]),
        ("5:0:3", [0, 0, 5]),
        ("7:0:0", [0, 0, 7]),
        # fmt: on
    ],
)
def test_parse_fuzz_duration_triplet_min_and_max_only(inp: str, exp: List[int]) -> None:
    assert parse_fuzz_duration_triplet(inp) == exp


@pytest.mark.parametrize(
    "inp",
    [
        # fmt: off
        "",
        "-",
        "-1",
        "1:-2:3",
        "0::1:2",
        "0:1:2:",
        ":0:1:2:",
        ":0:1:2",
        # fmt: on
    ],
)
def test_parse_bb_fuzz_duration_bad_format(inp: str) -> None:
    with pytest.raises(StopConditionError):
        assert parse_fuzz_duration_triplet(inp)


@pytest.mark.parametrize(
    "env_vars, duration_triplet",
    [
        # fmt: off
        ({"IRRELEVANT_VAR": "123"}, [0, 0, 600]),
        ({"FUZZ_DURATION": "456"}, [0, 0, 456]),
        ({"CERT_FUZZ_DURATION": "789"}, [0, 789, 0]),
        ({"CERT_FUZZ_LEVEL": "4"}, [0, 7200, 0]),
        ({"FUZZ_DURATION": "30", "CERT_FUZZ_LEVEL": "4"}, [0, 7200, 0]),
        # fmt: on
    ],
)
def test_detect_required_stop_condition_new(
    env_vars: Dict[str, str], duration_triplet: List[int]
) -> None:
    with mock.patch.dict(os.environ, env_vars, clear=True):
        ret = detect_required_stop_condition()
        assert ret == duration_triplet


@pytest.mark.parametrize(
    "triplet, explanation",
    [
        # fmt: off
        ([  0,   0,   0], "fuzz until stopped by user"),
        ([  0,   0, 600], "fuzz for 600 seconds"),
        ([  0, 100, 600], "fuzz until time without finds reaches 100 seconds\nbut for no longer than 600 seconds"),
        ([  0, 100,   0], "fuzz until time without finds reaches 100 seconds"),
        ([120,  60,   0], "fuzz for at least 120 seconds\nuntil time without finds reaches 60 seconds"),
        ([120,  60, 300], "fuzz for at least 120 seconds\nuntil time without finds reaches 60 seconds\nbut for no longer than 300 seconds"),
        # fmt: on
    ],
)
def test_explain_stop_conditions(triplet: List[int], explanation: str) -> None:
    assert explain_stop_conditions(triplet) == explanation
