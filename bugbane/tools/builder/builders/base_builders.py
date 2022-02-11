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

"""
Module defines Builder ABC class and its two main subclasses GCCBuilder and LLVMBuilder
"""

from typing import List, Dict, Optional

from abc import ABC, abstractmethod


import os
import shutil

import logging

log = logging.getLogger(__name__)

from bugbane.modules.process import run_shell_cmd, make_env_shell_str
from bugbane.modules.build_type import BuildType


class BuildError(Exception):
    """Exception class for errors that happen in Builder class"""


class UnsupportedBuildException(BuildError):
    """Exception used by builders to signal that they don't support requested BuildType"""


class Builder(ABC):
    """
    ABC for builders
    """

    CC = None
    CXX = None
    LD = None

    EXTRA_ENV = {}
    """Common env variables for each build command"""

    REQUIRED_BUILDS = {}
    """Required BuildTypes, e.g. BASIC and COVERAGE"""

    def __init__(self):
        self.build_cmd: Optional[str] = None
        self.build_types: Optional[List[BuildType]] = []
        self.build_root: Optional[str] = None
        self.build_store_dir: Optional[str] = None
        self.build_log_path: Optional[str] = None

    def configure(self, build_cmd, build_root, build_store_dir, build_log_path):
        self.build_cmd = build_cmd
        self.build_types = []
        self.build_root = build_root
        self.build_store_dir = build_store_dir
        self.build_log_path = build_log_path

    @abstractmethod
    def build_all(self) -> List[BuildType]:
        """
        Cycle through all the required build options, call self.build_one() for each one.
        Return list of BuildType objects for each successfull build
        """

    @abstractmethod
    def _prep_store_dir(self):
        """Create output directory for builds"""

    @abstractmethod
    def _init_build_log(self):
        """
        Create empty build log file
        """

    @abstractmethod
    def build_one(self, bt: BuildType):
        """Perform one build"""

    @abstractmethod
    def create_build_env(self, bt: BuildType) -> Dict[str, str]:
        """
        Generate dictionary of environment variables, such as:
            CFLAGS, AFL_USE_ASAN, etc.
        Env vars CC, CXX, LD are set by class variables.
        self.EXTRA_VARS may contain common flags defined by parent class
        """

    @abstractmethod
    def run_build_cmd(self, extra_env=None):
        ...

    @abstractmethod
    def _append_build_log(self, text: str, extra_env: dict):
        ...

    @abstractmethod
    def store_build(self, bt: BuildType):
        """Save build to separate directory"""

    @abstractmethod
    def assign_build_types(self, build_types: Optional[List[str]] = None):
        """
        Apply sanitizers, coverage, and other settings to this Builder instance.
        Settings are applied for all builds at once.
        """

    @abstractmethod
    def ensure_required_build_types(self):
        """
        Append REQUIRED_BUILDS to self.build_types
        """

    @abstractmethod
    def get_coverage_type(self) -> str:
        """
        Return coverage collection type
        """


class GCCBuilder(Builder):
    """
    GCC builder for C/C++ applications.
    Able to produce build types BASIC and COVERAGE.
    NOTE: for any other build type will produce BASIC build.
    """

    CC = "gcc"
    CXX = "g++"
    LD = "gcc"

    EXTRA_ENV = {
        "CFLAGS": "-g -fno-omit-frame-pointer",
        "CXXFLAGS": "-g -fno-omit-frame-pointer",
    }

    REQUIRED_BUILDS = {
        BuildType.BASIC,
        BuildType.COVERAGE,
    }

    # TODO: move common method realizations to BaseBuilder

    def build_all(self) -> List[BuildType]:
        succ_builds = []
        try:
            self._prep_store_dir()
            self._init_build_log()
            for build_type in self.build_types:
                log.info("Building %s", build_type.name.upper())
                os.makedirs(self.build_root, exist_ok=True)
                try:
                    self.build_one(build_type)
                except UnsupportedBuildException:
                    log.warning(
                        "build type %s is not supported by %s - skipped",
                        build_type.name.upper(),
                        self.__class__.__name__,
                    )
                else:
                    self.store_build(build_type)
                    succ_builds.append(build_type)
        except OSError as e:
            raise BuildError(f"while trying to make builds: {e}") from e

        return succ_builds

    def _prep_store_dir(self):
        """Create output directory for builds"""
        if os.path.exists(self.build_store_dir):
            shutil.rmtree(self.build_store_dir)
        os.makedirs(self.build_store_dir)

    def _init_build_log(self):
        """
        Create empty build log file
        """

        if not self.build_log_path:
            return

        open(self.build_log_path, "wt").close()

    def build_one(self, bt: BuildType):
        """Perform one build"""
        extra_env = self.create_build_env(bt)
        extra_env = {
            k: v for k, v in extra_env.items() if v
        }  # remove empty variables (e.g. default CFLAGS)
        extra_env.update({"CC": self.CC, "CXX": self.CXX, "LD": self.LD})
        self.run_build_cmd(extra_env=extra_env)

    def create_build_env(self, bt: BuildType) -> Dict[str, str]:
        """
        Generate dictionary of environment variables, such as:
            CFLAGS, AFL_USE_ASAN, etc.
        Env vars CC, CXX, LD are set by class variables.
        self.EXTRA_VARS may contain common flags defined by parent class
        """
        extra_env = self.EXTRA_ENV.copy()

        cur_env = os.environ.copy()
        for var in extra_env:
            if var in cur_env:
                extra_env[var] = cur_env[var]

        if bt == BuildType.COVERAGE:
            cov_flags = "--coverage"
            for var in extra_env:
                extra_env[var] += " -O0 " + cov_flags
            extra_env.update({"LDFLAGS": f"{cov_flags} -lgcov"})

        return extra_env

    def run_build_cmd(self, extra_env=None):
        log.debug("running cmd '%s' with extra env: %s", self.build_cmd, extra_env)
        ex_code, _, output = run_shell_cmd(
            cmd=self.build_cmd, extra_env=extra_env, timeout_sec=7200
        )
        output = output.decode(errors="replace")
        self._append_build_log(text=output, extra_env=extra_env)
        if ex_code != 0:
            raise BuildError(
                f"ERROR: while running '{self.build_cmd}' with extra env {extra_env}:\n{output}"
            )

    def _append_build_log(self, text: str, extra_env: dict):
        if not self.build_log_path:
            return
        env_str = make_env_shell_str(extra_env) or ""
        if env_str:
            env_str = "env " + env_str + " "

        with open(self.build_log_path, "at") as f:
            print(f"$ {env_str}{self.build_cmd}\n\n{text}\n\n", file=f)

    def store_build(self, bt: BuildType):
        """Save build to separate directory"""
        dest = os.path.join(self.build_store_dir, bt.dirname())
        if bt != BuildType.COVERAGE:
            log.verbose1("Moving results of %s build to %s", bt.name.upper(), dest)
            shutil.move(self.build_root, dest)
        else:
            # coverage build usually contains gcno files
            # it's better to not move them from original place
            log.verbose1("Copying results of %s build to %s", bt.name.upper(), dest)
            shutil.copytree(self.build_root, dest)

    def assign_build_types(self, build_types: Optional[List[str]] = None):
        """
        Apply sanitizers, coverage, and other settings to this Builder instance.
        Settings are applied for all builds at once.
        """

        if build_types:
            bts = {BuildType.from_str(bt) for bt in set(build_types)}
        else:
            bts = {BuildType.BASIC}

        self.build_types = sorted(bts, key=lambda bt: bt.value)

    def ensure_required_build_types(self):
        bts = self.REQUIRED_BUILDS.union(set(self.build_types))
        self.build_types = sorted(bts, key=lambda bt: bt.value)

    def get_coverage_type(self) -> str:
        return "lcov"


class LLVMBuilder(GCCBuilder):
    """
    LLVM/clang builder for C/C++ applications.
    Able to produce build types BASIC and COVERAGE.
    NOTE: for any other build type will produce BASIC build.
    """

    CC = "clang"
    CXX = "clang++"
    LD = "clang"

    EXTRA_ENV = {
        "CFLAGS": "-gline-tables-only -fno-omit-frame-pointer",
        "CXXFLAGS": "-gline-tables-only -fno-omit-frame-pointer",
    }

    REQUIRED_BUILDS = {
        BuildType.BASIC,
        BuildType.LAF,
        BuildType.CMPLOG,
        BuildType.COVERAGE,
    }

    def create_build_env(self, bt: BuildType) -> Dict[str, str]:
        """
        Similar to GCCBuilder but doesn't include -lgcov in LDFLAGS
        """

        extra_env = super().create_build_env(bt)

        flag = "LDFLAGS"
        if flag in extra_env:
            value = extra_env[flag]
            value = value.replace("-lgcov", "").strip()

            if value:
                extra_env[flag] = value
            else:
                del extra_env[flag]

        return extra_env

    def get_coverage_type(self) -> str:
        return "lcov-llvm"
