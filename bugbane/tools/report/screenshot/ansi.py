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
Convert ANSI text to png:
    ansifilter + pango-view
"""

import os
import shutil
import tempfile

from .screenshot import ScreenshotMaker, ScreenshotError
from .factory import ScreenshotMakerFactory

from bugbane.modules.process import run_shell_cmd


@ScreenshotMakerFactory.register("pango")
class AnsiDumpScreenshotMaker(ScreenshotMaker):
    """Call ansifilter & pango-view"""

    def __init__(self):
        super().__init__()
        self.color_map_path = None
        self._create_temp_workdir()

    def __del__(self):
        if os.path.exists(self.temp_workdir):
            shutil.rmtree(self.temp_workdir)

    def _create_temp_workdir(self):
        try:
            self.temp_workdir = tempfile.mkdtemp()
            self.color_map_path = os.path.join(self.temp_workdir, "color.map")
            with open(self.color_map_path, "wt") as f:
                f.write("7= #447422\n10= #885522\n11= #558822\n14= #4444aa\n")
        except OSError as e:
            raise ScreenshotError(
                f"error while creating ansifilter color map file: {e}"
            ) from e

    def convert(self, input_file_path: str, output_file_path: str, dpi: int):
        cmd = ""

        if shutil.which("ansifilter") is not None:
            pangoinput = os.path.join(self.temp_workdir, "screen.pango")
            cmd += f"ansifilter -i {input_file_path} --map {self.color_map_path} -M -o {pangoinput} && "
            cmd += "pango-view --markup "
        else:
            pangoinput = input_file_path
            cmd += "pango-view "

        cmd += f"--dpi {dpi} --font=mono -qo {output_file_path} {pangoinput}"

        exit_code, _, output = run_shell_cmd(cmd, timeout_sec=10)
        output = output.decode(errors="replace")
        if exit_code != 0:
            raise ScreenshotError(
                f"got bad exit code {exit_code} while converting {input_file_path} to {output_file_path}: \n{output}"
            )
