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

from typing import Dict

import os
import logging

log = logging.getLogger(__name__)

from bugbane.modules.file_utils import (
    none_on_bad_nonempty_dir,
    none_on_bad_nonempty_file,
)
from bugbane.modules.build_type import BuildType


class BuildDetectionError(Exception):
    """Exception class for errors during build detection"""


def get_builds(suite: str, tested_binary_path: str) -> Dict[BuildType, str]:
    """
    Convinience wrapper around detect_builds method
    """
    builds = detect_builds(suite, tested_binary_path)
    if not any(bt.is_fuzz_target() for bt in builds):
        log.error("Fuzz target build missing in input fuzzing suite")
        raise BuildDetectionError("fuzz target build missing")

    if not any(bt.is_coverage() for bt in builds):
        log.error("Coverage build missing in input fuzzing suite")
        raise BuildDetectionError("coverage build missing")

    return builds


def detect_builds(suite: str, tested_binary_path: str) -> Dict[BuildType, str]:
    """
    Enumerate directories (defined by BuildType) in suite path.
    """
    log.trace("suite: %s, tested_binary_name: %s", suite, tested_binary_path)

    if not suite or not tested_binary_path:
        return {}

    suite_dir = none_on_bad_nonempty_dir(suite)
    if suite_dir is None:
        return {}

    result = {}
    for bt in BuildType:
        subdir = bt.dirname()
        app = tested_binary_path.replace("$BUILD_ROOT", subdir)
        app_path = os.path.join(suite_dir, app)
        log.trace("looking for binary %s...", app_path)
        app_path = none_on_bad_nonempty_file(app_path)
        if app_path is None:
            continue
        log.verbose1(
            "[*] Found %s build: %s%s",
            bt.name,
            app_path,
            " (sanitizer)" if bt.is_static_sanitizer() else "",
        )
        result[bt] = app_path

    return result
