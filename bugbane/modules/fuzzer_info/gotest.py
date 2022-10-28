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

from typing import Optional

import os

from .gofuzz import GoFuzzInfo
from .factory import FuzzerInfoFactory


@FuzzerInfoFactory.register("go-test")
class GoTestInfo(GoFuzzInfo):
    REPRODUCE_REQUIRED = True

    COVERAGE_REQUIRED = False  # go test should be started with -test.coverprofile

    def initial_samples_required(self) -> bool:
        return False

    def input_dir(self, sync_dir: str) -> str:
        # FIXME: this will not work, need concrete subdirectory for FuzzXxx function
        return os.path.join(sync_dir, "corpus")

    def sample_mask(self, sync_dir: str, instance_name: str) -> str:
        instance_name = "*"  # TODO: get instance_name from -test.fuzz option
        return os.path.join(sync_dir, instance_name, "*")

    def crash_mask(self, sync_dir: str, instance_name: str) -> str:
        instance_name = "*"  # TODO: get instance_name from -test.fuzz option
        run_dir = self.stats_dir(sync_dir)

        return os.path.normpath(
            os.path.join(run_dir, "testdata", "fuzz", instance_name, "*")
        )

    def hang_mask(self, sync_dir: str, instance_name: str) -> str:
        # NOTE: gdb traces of compiled `go test` binary don't show user code,
        # instead they consist of `go test` code.
        # This was tested on sleeps and infinite cycles.
        # Hence we don't reproduce hangs
        return ""

    def coverage_dir(self, sync_dir: str) -> Optional[str]:
        return sync_dir

    def can_continue_after_bug(self) -> bool:
        # https://github.com/golang/go/issues/48127
        return False
