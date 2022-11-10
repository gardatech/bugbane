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


from typing import Dict, Any, Optional
from dataclasses import dataclass

import os

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.builds import BuildDetectionError, get_builds, BuildType
from bugbane.modules.fuzzer_cmd.factory import FuzzerCmdFactory


class ConfigError(Exception):
    """Exception class for errors in configuration reader classes."""


class FuzzConfigError(ConfigError):
    """Exception class for errors in FuzzConfig class."""


@dataclass
class FuzzConfig:
    """
    Holds settings used for to start fuzzing.
    NOTE: the data validation is only happening in from_dict method.
    """

    tested_binary_path: str
    run_args: str
    run_env: Dict[str, str]
    fuzz_cores: int
    timeout: Optional[int]
    src_root: str
    fuzzer_type: str
    builds: Dict[BuildType, str]

    @classmethod
    def from_dict(cls, suite_dir: str, config_vars: Dict[str, Any]) -> "FuzzConfig":
        """
        Create new FuzzConfig instance from variables read from config file.
        `suite_dir` is path where fuzzing builds are stored.
        Raise FuzzConfigError on validation errors.
        """

        cfg = config_vars
        try:
            tested_binary_path = cfg["tested_binary_path"]
            src_root = cfg["src_root"]
            run_args = cfg.get("run_args") or ""
            run_env = cfg.get("run_env") or {}
            fuzzer_type = cfg["fuzzer_type"]

            if fuzzer_type not in FuzzerCmdFactory.registry:
                supported = ", ".join(sorted(FuzzerCmdFactory.registry.keys()))
                raise FuzzConfigError(
                    f"invalid fuzzer type '{fuzzer_type}'. Supported fuzzers: {supported}"
                )

            fuzz_cores = int(cfg["fuzz_cores"])
            if fuzz_cores < 1:
                raise FuzzConfigError(
                    f"value '{fuzz_cores}' is not valid for fuzz cores"
                )

            timeout = cfg.get("timeout")
            if timeout is not None:
                timeout = int(timeout)
                if timeout < 1:
                    raise FuzzConfigError(f"value '{timeout}' is too small for timeout")

            builds = get_builds(suite_dir, tested_binary_path)

        except ValueError as e:
            raise FuzzConfigError(
                f"invalid data in one of the fields: fuzz_cores, timeout. Error message: {e}"
            ) from e
        except KeyError as e:
            raise FuzzConfigError(f"required variable wasn't found: {e}") from e
        except BuildDetectionError as e:
            raise FuzzConfigError(f"while trying to detect builds: {e}") from e

        config = cls(
            tested_binary_path=tested_binary_path,
            src_root=src_root,
            run_args=run_args,
            run_env=run_env,
            fuzz_cores=fuzz_cores,
            timeout=timeout,
            fuzzer_type=fuzzer_type,
            builds=builds,
        )
        return config

    def update_config_vars(
        self,
        config_vars: Dict[str, Any],
        fuzz_sync_dir: str,
        stop_conditions: Dict[str, Any],
        fuzz_time_real_seconds: int,
        reproduce_specs: Dict[str, Any],
    ) -> None:
        """
        Updates configuration file with current fields and variables provided.
        Other existing settings in the file are kept unchanged.
        """

        cfg = config_vars

        cfg["sanitizers"] = [
            bt.name for bt, _ in self.builds.items() if bt.is_static_sanitizer()
        ]
        cfg["run_args"] = self.run_args
        cfg["run_env"] = self.run_env
        cfg["fuzz_cores"] = self.fuzz_cores
        cfg["fuzz_sync_dir"] = fuzz_sync_dir
        cfg["stop_conditions"] = stop_conditions
        cfg["fuzz_time_real_seconds"] = fuzz_time_real_seconds
        cfg["reproduce_specs"] = reproduce_specs
