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

from .fuzzer_info import FuzzerInfo
from .factory import FuzzerInfoFactory


@FuzzerInfoFactory.register("libFuzzer")
class LibFuzzerInfo(FuzzerInfo):
    def initial_samples_required(self) -> bool:
        return False

    def input_dir(self, sync_dir: str) -> str:
        return sync_dir

    def sample_mask(self, sync_dir: str, instance_name: str) -> str:
        return os.path.join(sync_dir, "*")

    def crash_mask(self, sync_dir: str, instance_name: str) -> str:
        base_dir = os.path.dirname(os.path.normpath(sync_dir))
        return os.path.join(base_dir, "artifacts", "crash-*")

    def hang_mask(self, sync_dir: str, instance_name: str) -> str:
        base_dir = os.path.dirname(os.path.normpath(sync_dir))
        return os.path.join(base_dir, "artifacts", "timeout-*")

    def stats_dir(self, sync_dir: str) -> str:
        """
        libFuzzer "stats" directory is right outside sync_dir (should contain logs)
        """
        norm = os.path.normpath(sync_dir)
        num = len(norm.split(os.sep))
        if num <= 1:
            return os.path.join(norm, "..")

        return os.path.dirname(norm)

    def coverage_dir(self, sync_dir: str) -> Optional[str]:
        return None
