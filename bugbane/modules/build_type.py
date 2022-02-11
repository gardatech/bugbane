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

from enum import Enum, auto


class BuildType(Enum):
    BASIC = auto()
    GOFUZZ = auto()
    LAF = auto()
    CMPLOG = auto()
    ASAN = auto()
    UBSAN = auto()
    CFISAN = auto()
    TSAN = auto()
    LSAN = auto()
    MSAN = auto()
    COVERAGE = auto()  # coverage build should be the last

    @classmethod
    def from_str(cls, s: str):
        if not s:
            return cls.BASIC

        up = s.upper()
        if up == "COV":
            return cls.COVERAGE

        for bt in cls:
            if up == bt.name.upper():
                return bt

        raise RuntimeError(
            f"bad build type {s} (supported types: {', '.join(bt.name.upper() for bt in cls)})"
        )

    def dirname(self):
        return self.name.lower()

    def is_static_sanitizer(self):
        return self in (
            BuildType.ASAN,
            BuildType.UBSAN,
            BuildType.CFISAN,
            BuildType.TSAN,
            BuildType.LSAN,
            BuildType.MSAN,
        )

    def is_coverage(self):
        """
        This build allows to collect coverage information
        """
        return self in (BuildType.GOFUZZ, BuildType.COVERAGE)

    def is_fuzz_target(self):
        """
        This build can be used as fuzz target, e.g. afl-fuzz ... -- ./app <args>
        """
        return self.is_for_fuzz() and not self.is_fuzz_helper()

    def is_for_fuzz(self):
        """
        This build can be used during fuzzing process
        (basic, sanitizers, cmplog, laf, etc. except for coverage)
        """
        return self not in (BuildType.COVERAGE,)

    def is_fuzz_helper(self):
        """
        This build can be used during fuzzing, but can't be used as fuzz target
        (symcc build for AFL++, cmplog build etc)
        """
        return self in (BuildType.CMPLOG,)
