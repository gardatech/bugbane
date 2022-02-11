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

import logging

log = logging.getLogger(__name__)

from bugbane.modules.process import checked_run_shell_cmd

from .collector import CoverageCollector, CoverageCollectorError
from .factory import CoverageCollectorFactory


@CoverageCollectorFactory.register("llvm")
class LLVMCoverageCollector(CoverageCollector):
    # TODO: implement as in prepare-code-coverage-artifact
    def cleanup_coverage_info(self):
        raise NotImplementedError()

    def generate_report(self, report_dir: str, include_source: bool = True):
        raise NotImplementedError()
