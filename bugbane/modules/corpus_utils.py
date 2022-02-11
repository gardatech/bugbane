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

import os
import logging

log = logging.getLogger(__name__)


def ensure_initial_corpus_exists(path: str):
    """
    Creates simple initial corpus if it doesn't exist
    """

    log.trace("path = %s", path)

    if os.path.exists(path):
        if not os.path.isdir(path):
            raise OSError(f"{path} can't be used as corpus directory")

        for p in os.listdir(path):
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                return  # have directory with some nonempty files
    else:
        log.debug("Creating initial corpus directory %s", path)
        os.makedirs(path)

    sample_path = os.path.join(path, "1")
    log.debug("Creating one initial sample %s", sample_path)
    with open(sample_path, "wb") as f:
        f.write(b"12345")
