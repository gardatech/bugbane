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

from typing import Dict, Callable, Optional

import os
import glob
import hashlib
import logging

log = logging.getLogger(__name__)

from .minimizer import Minimizer, MinimizerError

# intentionally not registered in MinimizerFactory
class HashSumMinimizer(Minimizer):
    """Minimizer based on SHA1 hashes of files"""

    def __init__(self):
        super().__init__()
        self.hashes: Dict[str, str] = {}

    def run_one(
        self,
        mask: str,
        dest: str,
        file_action_func: Callable[[str, str], None],
    ) -> Optional[int]:
        samples = glob.glob(mask)
        log.verbose2("Have %d samples for mask '%s'", len(samples), mask)
        for sample in samples:
            file_hash = self.hash_one_sample(sample)
            if file_hash is None:
                continue
            if file_hash in self.hashes:
                continue
            self.hashes[file_hash] = sample
            dest_file_path = os.path.join(dest, file_hash)
            file_action_func(sample, dest_file_path)

        return len(self.hashes)

    def hash_one_sample(
        self, sample_path: str, readsize: int = 2**19
    ) -> str:  # 2**19 = 512 Kb
        h = hashlib.sha1()

        if not sample_path or not os.path.isfile(sample_path):
            return None

        try:
            with open(sample_path, "rb") as f:
                while True:
                    data = f.read(readsize)
                    if not data:
                        break
                    h.update(data)
        except OSError as e:
            raise MinimizerError(f"during hashing of file '{sample_path}': {e}") from e

        return h.hexdigest()
