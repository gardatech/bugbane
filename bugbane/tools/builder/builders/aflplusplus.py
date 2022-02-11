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

from .base_builders import GCCBuilder, LLVMBuilder, UnsupportedBuildException
from .factory import FuzzBuilderFactory


@FuzzBuilderFactory.register("AFL++LLVM")
class AFLplusplusLLVMBuilder(LLVMBuilder):
    """
    LLVMBuilder capable of passing AFL++ env variables according to desired build type
    This builder uses afl-clang-fast/++ compilers.
    """

    CC = "afl-clang-fast"
    CXX = "afl-clang-fast++"
    LD = "afl-clang-fast"

    def create_build_env(self, bt: BuildType) -> Dict[str, str]:
        extra_env = super().create_build_env(bt)

        if bt == BuildType.LAF:
            extra_env.update({"AFL_LLVM_LAF_ALL": "1"})
        elif bt == BuildType.CMPLOG or bt.is_static_sanitizer():
            extra_env.update({"AFL_USE_" + bt.name.upper(): "1"})

        return extra_env


@FuzzBuilderFactory.register("AFL++LLVM-LTO")
class AFLplusplusLLVMLTOBuilder(AFLplusplusLLVMBuilder):
    """
    LLVMBuilder capable of passing AFL++ env variables according to desired build type
    This builder uses afl-clang-lto/++ compilers.
    """

    CC = "afl-clang-lto"
    CXX = "afl-clang-lto++"
    LD = "afl-clang-lto"


@FuzzBuilderFactory.register("AFL++GCC")
class AFLplusplusGCCBuilder(GCCBuilder):
    """
    GCCBuilder capable of passing AFL++ env variables according to desired build type
    This builder uses deprecated afl-gcc/++ compilers that don't support persistent fuzzing mode.
    """

    CC = "afl-gcc"
    CXX = "afl-g++"
    LD = "afl-gcc"

    def create_build_env(self, bt: BuildType) -> Dict[str, str]:
        extra_env = super().create_build_env(bt)
        log.trace(
            "parent %s returned extra_env: %s", super().__class__.__name__, extra_env
        )

        if bt.is_static_sanitizer():
            extra_env.update({"AFL_USE_" + bt.name.upper(): "1"})
        elif bt not in (BuildType.BASIC, BuildType.COVERAGE):
            raise UnsupportedBuildException(f"unsupported build type {bt.name.upper()}")
        log.trace("returning extra_env: %s", extra_env)
        return extra_env


@FuzzBuilderFactory.register("AFL++GCC-PLUGIN")
class AFLplusplusGCCPluginBuilder(AFLplusplusGCCBuilder):
    """
    GCCBuilder capable of passing AFL++ env variables according to desired build type.
    This builder uses afl-gcc/++-fast compilers that support persistent fuzzing mode.
    """

    CC = "afl-gcc-fast"
    CXX = "afl-g++-fast"
    LD = "afl-gcc-fast"
