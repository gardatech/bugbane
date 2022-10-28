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
from bugbane.modules.log import getLogger


log = getLogger(__name__)

from .factory import ReproducerFactory
from .reproducer import ReproducerError
from .default_reproducer import DefaultReproducer


@ReproducerFactory.register("go-test")
class GoTestReproducer(DefaultReproducer):
    """
    Reproducer for `go test` fuzzer.
    Similar to DefaultReproducer, but respects `go test` run syntax.
    """

    def prep_run_args(self, sample_path: str) -> str:
        """
        Prepares arguments for one `go test` run for given sample.
        For given sample return string like "-test.run=FuzzXxx/sample_name".
        """
        sample = os.path.normpath(sample_path)
        parts = sample.split(os.sep)
        arg = "/".join(parts[-2:])
        return f"-test.run={arg}"
