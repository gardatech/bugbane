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

from .lcov import LCOVCoverageCollector
from .factory import CoverageCollectorFactory


@CoverageCollectorFactory.register("lcov-llvm")
class LCOV_LLVM_CoverageCollector(LCOVCoverageCollector):
    """
    Class suitable for collecting coverage using lcov (uses gcov) and genhtml.

    ONLY for targets built with LLVM/clang and GCC-compatible coverage flags (--coverage, -lgcov).

    NOTE: will generate 0% coverage reports for targets built with GCC.
    NOTE: will NOT work for targets built with LLVM source-based coverage (-fprofile-instr-generate -fcoverage-mapping).
    """

    def _make_lcov_capture_cmd(self):
        """
        Generate lcov --capture command with use of gcov-tool
        that calls execvp llvm-cov gcov
        """
        cmd = super()._make_lcov_capture_cmd()
        cmd += " --gcov-tool llvm-gcov-tool"
        return cmd
