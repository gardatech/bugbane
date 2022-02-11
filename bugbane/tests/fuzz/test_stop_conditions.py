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

from pytest_mock import MockerFixture

from bugbane.modules.stats.fuzz.aflplusplus import AFLplusplusFuzzStats
from bugbane.tools.fuzz.stop_conditions import (
    real_run_time,
    time_without_finds,
    total_run_time,
)

TIME_MOCK_PATH = "bugbane.tools.fuzz.stop_conditions.time"


def test_real_run_time(mocker: MockerFixture):
    mocker.patch(TIME_MOCK_PATH, return_value=129)

    stats = AFLplusplusFuzzStats(num_instances=4, start_timestamp=100)

    assert not real_run_time(stats, 30)
    assert real_run_time(stats, 29)
    assert real_run_time(stats, 1)


def test_total_run_time(mocker: MockerFixture):
    mocker.patch(TIME_MOCK_PATH, return_value=150)

    stats = AFLplusplusFuzzStats(num_instances=4, start_timestamp=100)

    assert not total_run_time(stats, 201)
    assert total_run_time(stats, 200)
    assert total_run_time(stats, 1)


def test_time_without_finds(mocker: MockerFixture):
    mocker.patch(TIME_MOCK_PATH, return_value=159)

    # last path timestamp not yet loaded
    stats = AFLplusplusFuzzStats(
        num_instances=4, last_path_timestamp=0, start_timestamp=100
    )
    assert not time_without_finds(stats, 30)

    stats = AFLplusplusFuzzStats(
        num_instances=4, last_path_timestamp=130, start_timestamp=100
    )
    assert time_without_finds(stats, 28)
    assert time_without_finds(stats, 29)
    assert not time_without_finds(stats, 30)
    assert not time_without_finds(stats, 31)
