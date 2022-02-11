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


@FuzzerInfoFactory.register("AFL++")
class AFLplusplusInfo(FuzzerInfo):
    def initial_samples_required(self) -> bool:
        return True

    def input_dir(self, sync_dir: str) -> str:
        return os.path.normpath(os.path.join(sync_dir, "..", "in"))

    def sample_mask(self, sync_dir: str, instance_name: str) -> str:
        return os.path.join(sync_dir, instance_name, "queue", "id*")

    def crash_mask(self, sync_dir: str, instance_name: str) -> str:
        return os.path.join(sync_dir, instance_name, "crashes", "id*")

    def hang_mask(self, sync_dir: str, instance_name: str) -> str:
        return os.path.join(sync_dir, instance_name, "hangs", "id*")

    def stats_dir(self, sync_dir: str) -> str:
        """
        AFL++ stats directory is same as sync_dir
        """
        return sync_dir

    def coverage_dir(self, sync_dir: str) -> Optional[str]:
        return None
