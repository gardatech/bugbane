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

from typing import Dict, Optional, List
from time import time

import os
from bugbane.errors import BugBaneException
from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats


class StopConditionError(BugBaneException):
    """Exception class for errors that happen in stop condition related routines"""


def detect_required_stop_condition(
    environ: Optional[Dict[str, str]] = None
) -> List[int]:
    """
    Checks `environ` for the values of certain variables.
    Returns list: [minimum fuzz duration required, time without finds wanted, maximum fuzz duration allowed]

    Legacy env variables supported:
        env var CERT_FUZZ_DURATION set? -> [0, time_without_finds with specified time, 0]
        env var CERT_FUZZ_LEVEL set? -> [0, time_without_finds with predefined time, 0]
        env var FUZZ_DURATION set? -> [0, 0, real_run_time with specified time]

    New FUZZ_DURATION format supported: "MIN_TIME:TIME_WITHOUT_FINDS:MAX_TIME",
        e.g. "400:200:800" -> [400, 200, 800]

    If none of that was set:
        -> [0, 0, real_run_time = 600 seconds]
    """

    env = environ or os.environ

    cert_fuzz_duration_var = "CERT_FUZZ_DURATION"
    cert_fuzz_level_var = "CERT_FUZZ_LEVEL"
    ci_fuzz_duration_var = "FUZZ_DURATION"

    cert_fuzz_duration = env.get(cert_fuzz_duration_var)
    cert_fuzz_level = env.get(cert_fuzz_level_var)
    ci_fuzz_duration = env.get(ci_fuzz_duration_var)

    cert_fuzz_levels_time_without_finds = {
        4: 2 * 60 * 60,  # 4 уровень контроля -> 2 часа без новых путей
        3: 4 * 60 * 60,
        2: 8 * 60 * 60,
    }

    try:
        if cert_fuzz_duration is not None:
            log.warning(
                "using legacy environment variable %s, consider switching to the updated %s, which supports time without finds with min and max fuzzing duration limits",
                cert_fuzz_duration_var,
                ci_fuzz_duration_var,
            )
            return [0, int(cert_fuzz_duration), 0]

        if cert_fuzz_level is not None:
            log.warning(
                "using legacy environment variable %s, consider switching to the updated %s, which supports time without finds with min and max fuzzing duration limits",
                cert_fuzz_level_var,
                ci_fuzz_duration_var,
            )
            duration = cert_fuzz_levels_time_without_finds[int(cert_fuzz_level)]
            return [0, duration, 0]

        if ci_fuzz_duration is not None:
            triplet = parse_fuzz_duration_triplet(ci_fuzz_duration)
            return triplet

    except ValueError as e:
        raise StopConditionError(f"Bad environment variable value ({e})") from e
    except KeyError as e:
        supported_levels = ", ".join(
            str(x) for x in cert_fuzz_levels_time_without_finds
        )
        raise StopConditionError(
            f"Supported CERT_FUZZ_LEVEL values: {supported_levels}.\n"
            "For other options please use CERT_FUZZ_DURATION=<seconds>"
        ) from e

    log.warning(
        "Wasn't able to detect stop condition. Using default of 10 minutes run time"
    )
    return [0, 0, 10 * 60]


def parse_fuzz_duration_triplet(fuzz_duration_value: str) -> List[int]:
    """
    For the input `fuzz_duration_value` string such as "100:200:400"
    return a list of values such as [200, 100, 400] aka fuzz duration `triplet`.

    The values represent stop conditions:
        The first number (200) repsesents the minimum required fuzzing duration in seconds.
        The second number (100) represents the required time without finds in seconds.
        The third number (400) repsesents the maximum allowed fuzzing duration in seconds.

    If any value passed is 0, the corresponding stop condition is not used.
    When a string such as "400" is passed (instead of "0:0:400"), it's used as the max fuzz duration seconds (same as 0:0:400).

    Other examples:
        "0:123:456" -> [0, 123, 456]: fuzz until there's 123 seconds without new finds, but for no longer than 456 seconds
        "999:555:0" -> [999, 555, 0]: fuzz until there's 555 seconds without new finds, but at least for 999 seconds
        "100:0:200" -> [0, 0, 200]: min used without "time without finds", so we ignore it
        "100:0:50" -> [0, 0, 100]: min > max while no "time without finds", so we make max = min and min = 0
        "100:0:0" -> [0, 0, 100]: same as in previous example, min > max -> max = min, min = 0

    Some short forms are accepted too: ":1:2" is the same as "0:1:2", and "1:2:" is the same as "1:2:0"
    """

    v = fuzz_duration_value
    try:
        if ":" not in v:
            triplet = [0, 0, int(v)]
        else:
            if v[0] == ":":
                v = "0" + v

            if v[-1] == ":":
                v = v + "0"

            triplet = [int(s) for s in v.split(":")]

            if len(triplet) != 3:
                raise ValueError()

        for i in triplet:
            if i < 0:
                raise ValueError()

    except ValueError:
        raise StopConditionError(f"invalid fuzz duration value: {fuzz_duration_value}")

    t = triplet

    MIN_DURATION = 0
    TIME_WITHOUT_FINDS = 1
    MAX_DURATION = 2

    # "time without finds" not specified -> min becomes meaningless on its own ...
    if t[TIME_WITHOUT_FINDS] == 0:
        if t[MIN_DURATION] > t[MAX_DURATION]:  # ... unless it's larger than max
            t[MAX_DURATION] = t[MIN_DURATION]
        t[MIN_DURATION] = 0

    return t


def check_if_stop_conditions_are_met(
    stats: FuzzStats, fuzz_duration_triplet: List[int]
) -> Dict[str, int]:
    """
    Return non-empty dictionary if stop conditions for fuzzing are currently met.
    Return empty dictionary otherwise.

    Dictionary returned contains the main triggered stop condition and duration in seconds.
    Possible keys of dictionary returned: "time_without_finds", "real_run_time".
    """

    min_duration_required = fuzz_duration_triplet[0]
    seconds_without_finds_required = fuzz_duration_triplet[1]
    max_duration_allowed = fuzz_duration_triplet[2]

    if min_duration_required > 0 and seconds_without_finds_required < 1:
        if max_duration_allowed < min_duration_required:
            max_duration_allowed = min_duration_required

    now = int(time())
    current_duration = now - stats.start_timestamp

    min_duration_met = current_duration >= min_duration_required
    stamp = stats.last_path_timestamp
    time_without_finds_met = (
        stamp > 0 and (now - stamp) >= seconds_without_finds_required
    )
    max_duration_reached = current_duration >= max_duration_allowed

    # print(f"{min_duration_required=}, {seconds_without_finds_required=}, {max_duration_allowed=}")
    # print(f"{min_duration_met=}, {time_without_finds_met=}, {max_duration_reached=}")

    # NOTE: strings here are used in the report template
    #       also we divide by 60 here for the report tool

    if seconds_without_finds_required > 0 and time_without_finds_met:
        if min_duration_met:
            return {"minutes_without_paths": seconds_without_finds_required // 60}

    if max_duration_allowed > 0 and max_duration_reached:
        return {"minutes_run_time": max_duration_allowed // 60}

    return {}


def explain_stop_conditions(triplet: List[int]) -> str:
    """
    Return a multiline string explaining a given duration `triplet`.

    Example:
    triplet = [10800, 7200, 14400]

    Output:
    "fuzz for at least 10800 seconds
    until time without finds reaches 7200 seconds
    but for no longer than 14400 seconds"

    Note: it is expected for `triplet` to make sense,
    that is, do not pass a `triplet` like `[100, 0, 10]`,
    as this function will return bogus result.
    """
    t = triplet

    if t == [0, 0, 0]:
        return "fuzz until stopped by user"

    explanation: List[str] = []
    if t[0] > 0:
        if t[1] > 0:
            explanation.append(f"for at least {t[0]} seconds")
        else:
            explanation.append(f"for {t[0]} seconds")

    if t[1] > 0:
        explanation.append(f"until time without finds reaches {t[1]} seconds")

    if t[2] > 0:
        if t[1] > 0:
            explanation.append(f"but for no longer than {t[2]} seconds")
        else:
            explanation.append(f"for {t[2]} seconds")

    return "fuzz " + "\n".join(explanation)
