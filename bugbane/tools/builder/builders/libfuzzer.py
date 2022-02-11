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

from typing import Dict

from bugbane.modules.build_type import BuildType

import logging

log = logging.getLogger(__name__)

from .base_builders import LLVMBuilder, UnsupportedBuildException
from .factory import FuzzBuilderFactory


@FuzzBuilderFactory.register("libFuzzer")
class LibFuzzerBuilder(LLVMBuilder):
    """
    LLVMBuilder capable of passing libFuzzer env variables according to desired build type
    This builder uses clang/++ compilers.
    """

    EXTRA_ENV = {
        "CFLAGS": "-gline-tables-only -fno-omit-frame-pointer -fsanitize=fuzzer-no-link -fno-sanitize-recover=all",
        "CXXFLAGS": "-gline-tables-only -fno-omit-frame-pointer -fsanitize=fuzzer-no-link -fno-sanitize-recover=all",
        "LDFLAGS": "-fsanitize=fuzzer-no-link",
        "LIB_FUZZING_ENGINE": "-fsanitize=fuzzer",
    }

    REQUIRED_BUILDS = {
        BuildType.BASIC,
        BuildType.COVERAGE,
    }

    def create_build_env(self, bt: BuildType) -> Dict[str, str]:
        extra_env = super().create_build_env(bt)
        bt_mapping = {
            BuildType.ASAN: "-fsanitize=address",
            BuildType.UBSAN: "-fsanitize=undefined",
            BuildType.CFISAN: "-fsanitize=cfi",
            BuildType.MSAN: "-fsanitize=memory",
            BuildType.TSAN: "-fsanitize=thread",
            BuildType.LSAN: "-fsanitize=leak",
        }
        supported_bts = set(bt_mapping).union({BuildType.BASIC, BuildType.COVERAGE})
        if bt not in supported_bts:
            raise UnsupportedBuildException(
                f"BuildType {bt.name.upper()} is not supported in builder {self.__class__.__name__}"
            )

        if bt in bt_mapping:
            flags = " " + bt_mapping[bt]
            extra_env["CFLAGS"] += flags + " -O1"
            extra_env["CXXFLAGS"] += flags + " -O1"
            extra_env["LDFLAGS"] += flags

            if bt == BuildType.ASAN:
                extra_env["CFLAGS"] += " -fsanitize-address-use-after-scope"
                extra_env["CXXFLAGS"] += " -fsanitize-address-use-after-scope"

        return extra_env
