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

from typing import Callable, Dict, Optional, Tuple, Any
from time import time

import os
import logging

log = logging.getLogger(__name__)

from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats


class StopConditionError(Exception):
    """Exception class for errors that happen in stop condition related routines"""


class StopConditions:
    """
    Class that holds time-based stop conditions
    """

    registry: Dict[str, Callable[[FuzzStats, int], bool]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[FuzzStats, int], bool]:
        """Register stop condition in internal registry"""

        def wrapper(
            wrapped: Callable[[FuzzStats, int], bool]
        ) -> Callable[[FuzzStats, int], bool]:
            if name in cls.registry:
                log.warning("replacing '%s' in %s registry", name, cls.__name__)
            cls.registry[name] = wrapped
            return wrapped

        return wrapper

    @classmethod
    def get(cls, wanted_condition: str) -> Callable[[FuzzStats, int], bool]:
        """Return stop condition function"""
        if wanted_condition not in cls.registry:
            raise TypeError(
                f"stop condition {wanted_condition} is not registered in {cls.__name__}"
            )

        return cls.registry[wanted_condition]

    @classmethod
    def met(cls, wanted_condition: str, stats: FuzzStats, seconds: int) -> bool:
        """Check if stop condition met"""
        return cls.get(wanted_condition)(stats, seconds)


@StopConditions.register("time_without_finds")
def time_without_finds(stats: FuzzStats, seconds: int) -> bool:
    """The last new path was found N seconds ago (across all instances)"""
    now = int(time())
    stamp = stats.last_path_timestamp
    log.trace(
        "now=%s, stamp=%s, now-stamp=%s seconds=%s", now, stamp, now - stamp, seconds
    )
    return stamp > 0 and (now - stamp) >= seconds


@StopConditions.register("real_run_time")
def real_run_time(stats: FuzzStats, seconds: int) -> bool:
    """Actual test time is N or more seconds"""
    now = int(time())
    return (now - stats.start_timestamp) >= seconds


@StopConditions.register("total_run_time")
def total_run_time(stats: FuzzStats, seconds: int) -> bool:
    """
    Total run time (sum from all instances) is N or more seconds.
    FuzzStats holds the most old fuzzer start timestamp, so it is assumed that
    all fuzzers start at the same time.
    """
    now = int(time())
    return stats.num_instances * (now - stats.start_timestamp) >= seconds


def detect_required_stop_condition(
    environ: Optional[Dict[str, str]] = None, bane_vars: Optional[Dict[str, Any]] = None
) -> Tuple[str, int]:
    """
    Gets condition for stopping fuzzing job.
    Returns tuple: (stop condition function name, time in seconds).

    Note: bane_vars is not used as of now.

    Return first detected:
        env var CERT_FUZZ_DURATION set? -> time_without_finds with specified time
        env var CERT_FUZZ_LEVEL set? -> time_without_finds with predefined time
        env var FUZZ_DURATION set? -> real_run_time with specified time
        -> real_run_time with 10 minutes
    """

    env = environ or os.environ
    vars = bane_vars or {}

    log.trace("env size is %d, vars size is %d", len(env), len(vars))

    cert_fuzz_duration = env.get("CERT_FUZZ_DURATION")
    cert_fuzz_level = env.get("CERT_FUZZ_LEVEL")
    ci_fuzz_duration = env.get("FUZZ_DURATION")

    try:
        if cert_fuzz_duration is not None:
            return ("time_without_finds", int(cert_fuzz_duration))

        cert_fuzz_levels_time_without_finds = {
            4: 2 * 60 * 60,  # 4 уровень контроля -> 2 часа без новых путей
            3: 4 * 60 * 60,
            2: 8 * 60 * 60,
        }

        if cert_fuzz_level is not None:
            duration = cert_fuzz_levels_time_without_finds[int(cert_fuzz_level)]
            return ("time_without_finds", duration)

        if ci_fuzz_duration is not None:
            return ("real_run_time", int(ci_fuzz_duration))

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

    log.warning("Wasn't able to detect stop condition. Using default of 10 minutes")
    return ("real_run_time", 10 * 60)
