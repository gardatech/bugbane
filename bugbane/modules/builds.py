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

from typing import Dict

import os
from bugbane.modules.log import getLogger

log = getLogger(__name__)

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
        log.error(
            'Fuzzing build missing in input fuzzing suite or "tested_binary_path" is invalid'
        )
        log.error(
            'If your build is at /fuzz/asan/myapp, "tested_binary_path" should be set to just "myapp"'
        )
        raise BuildDetectionError("fuzz target build missing")

    if not any(bt.is_coverage() for bt in builds):
        log.error("Coverage build missing in input fuzzing suite")
        raise BuildDetectionError("coverage build missing")

    return builds


def detect_builds(suite: str, tested_binary_path: str) -> Dict[BuildType, str]:
    """
    Enumerate directories (defined by BuildType) in suite path.
    """
    log.trace("suite: %s, tested_binary_path: %s", suite, tested_binary_path)

    if not suite or not tested_binary_path:
        return {}

    suite_dir = none_on_bad_nonempty_dir(suite)
    if suite_dir is None:
        return {}

    result = {}
    for bt in BuildType:
        subdir = bt.dirname()

        # TODO: remove in future versions or reconsider
        tested_binary_path = tested_binary_path.replace("$BUILD_ROOT/", "")

        app = os.path.join(subdir, tested_binary_path)
        app_path = os.path.join(suite_dir, app)
        log.verbose3("Checking whether binary exists: %s", app_path)
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
