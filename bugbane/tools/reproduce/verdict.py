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

from enum import Enum


class Verdict(Enum):
    """
    Generalized verdict of application run
    """

    UNKNOWN = (0, "Wasn't able to determine verdict")
    NO_ERROR = (1, "No error occurred")
    WARNING_LONG_RUN = (2, "Target execution took more time than expected")
    HANG = (4, "Hang")
    CRASH_GENERIC = (8, "Crash")
    CRASH_SANITIZER = (16, "Sanitizer crash")
    CRASH_ASAN = (32, "AddressSanitizer:")
    CRASH_UBSAN = (64, "Undefined behavior")
    CRASH_CFISAN = (128, "Control flow intergity violation")
    CRASH_STACK_OVERFLOW = (256, "Stack overflow")
    CRASH_PANIC = (512, "Panic")

    def __init__(self, value, description):
        self._id = value
        self._description = description

    @property
    def id(self):
        return self._id

    @property
    def description(self):
        return self._description

    @classmethod
    def from_run_results(cls, exit_code, is_hang, output: str):
        """Make Verdict object from application run results"""

        if is_hang:
            return cls.HANG

        if not output:
            return cls.UNKNOWN

        if "program hanged (timeout" in output:
            return cls.HANG

        if "fatal error: stack overflow" in output:
            return cls.CRASH_STACK_OVERFLOW

        if "<HANG_START>" in output and "<HANG_END>" in output:
            return cls.HANG

        if (
            "Segmentation fault" in output
            or "Sanitizer:DEADLYSIGNAL" in output
            or "signal SIGSEGV: segmentation violation" in output
        ):
            return cls.CRASH_GENERIC

        if "runtime error: control flow integrity " in output:
            return cls.CRASH_CFISAN

        if "UndefinedBehaviorSanitizer:" in output:
            return cls.CRASH_UBSAN

        if "AddressSanitizer:" in output:
            return cls.CRASH_ASAN

        if "panic: " in output:
            return cls.CRASH_PANIC

        if exit_code is not None and exit_code > 128:
            return cls.CRASH_GENERIC

        if "Program received signal" in output or "runtime error:" in output:
            return cls.CRASH_GENERIC

        return cls.NO_ERROR
