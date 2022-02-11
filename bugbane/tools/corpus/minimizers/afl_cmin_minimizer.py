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

from typing import Callable, Optional

import os
import logging

log = logging.getLogger(__name__)

from bugbane.modules.process import run_shell_cmd

from .factory import MinimizerFactory
from .minimizer import MinimizerUsingProgram, MinimizerError


@MinimizerFactory.register("afl-cmin")
class AFL_cmin_Minimizer(MinimizerUsingProgram):
    def run_one(
        self,
        mask: str,
        dest: str,
        _file_action_func: Callable[[str, str], None],
    ) -> Optional[int]:
        if self.program is None:
            raise MinimizerError("minimizer not configured with program")

        newmask = self._sanitize_mask(mask)
        cmd = self._make_run_cmd(newmask, dest)
        exit_code, is_timeout, output = run_shell_cmd(cmd, timeout_sec=self.timeout_sec)
        if is_timeout:
            raise MinimizerError(f"timeout during minimization of samples at {mask}")

        log.verbose1(output.decode(errors="replace"))
        if exit_code != 0:
            raise MinimizerError(
                f"bad exit code {exit_code} during minimization of samples at {mask}"
            )

        return None  # TODO: maybe count files on disk

    @staticmethod
    def _sanitize_mask(mask: str):
        if mask.endswith("*"):
            m = mask[:-1]
        else:
            m = mask

        if "*" in m:
            raise MinimizerError(
                f"don't know how to expand mask {mask} for single run of afl-cmin"
            )

        return os.path.normpath(m)

    def _make_run_cmd(self, mask: str, dest: str):
        run_args = " ".join(self.run_args or [])
        cmd = f"afl-cmin -i {mask} -o {dest} -m none -- {self.program} {run_args}"
        return cmd
