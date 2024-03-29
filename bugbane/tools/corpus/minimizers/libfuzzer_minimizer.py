# Copyright 2022-2024 Garda Technologies, LLC. All rights reserved.
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

from typing import Callable, Optional

import os
from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.process import run_shell_cmd
from bugbane.modules.fuzzer_cmd.libfuzzer import LibFuzzerCmd

from .factory import MinimizerFactory
from .minimizer import MinimizerUsingProgram, MinimizerError


@MinimizerFactory.register("libFuzzer")
class LibFuzzerMinimizer(MinimizerUsingProgram):
    """Tool-based corpus minimizer using libFuzzer."""

    # NOTE: almost the same as afl-cmin, but no need for stdout shortening

    def run_one(
        self,
        mask: str,
        dest: str,
        _file_action_func: Callable[[str, str], None],
    ) -> Optional[int]:
        newmask = self._sanitize_mask(mask)
        cmd = self._make_run_cmd(newmask, dest)
        exit_code, is_timeout, output = run_shell_cmd(
            cmd, extra_env=self.run_env, timeout_sec=self.tool_timeout_sec
        )
        if is_timeout:
            raise MinimizerError(f"timeout during minimization of samples at {mask}")

        if output:
            decoded = output.decode(errors="replace")
            log.verbose1(decoded)
        else:
            log.warning("libFuzzer generated no output")

        if exit_code != 0:
            raise MinimizerError(
                f"bad exit code {exit_code} during minimization of samples at {mask}"
            )

        return self.count_files_in_dir(dest)

    @staticmethod
    def _sanitize_mask(mask: str):
        if mask.endswith("*"):
            m = mask[:-1]
        else:
            m = mask

        if "*" in m:
            raise MinimizerError(
                f'don\'t know how to expand mask {mask} for single run of libFuzzer with "-merge"'
            )

        return os.path.normpath(m)

    def _make_run_cmd(self, input_dir: str, dest_dir: str):
        if self.program is None:
            raise MinimizerError("minimizer not configured with program")

        cmd = f'"{self.program}" -merge=1 -rss_limit_mb=0 '
        if self.prog_timeout_ms is not None:
            self.prog_timeout_ms = LibFuzzerCmd.ceil_milliseconds_to_seconds(
                self.prog_timeout_ms
            )
            cmd += f"-timeout={self.prog_timeout_ms} "
        cmd += f'"{dest_dir}" "{input_dir}"'
        return cmd
