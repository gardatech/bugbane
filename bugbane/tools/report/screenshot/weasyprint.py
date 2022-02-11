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

import os
import shutil
import tempfile

from bugbane.modules.process import run_shell_cmd

from .screenshot import ScreenshotMaker, ScreenshotError
from .factory import ScreenshotMakerFactory


@ScreenshotMakerFactory.register("weasyprint")
class WeasyPrintScreenshotMaker(ScreenshotMaker):
    """Use weasyprint on input html"""

    def __init__(self):
        super().__init__()
        self.style_path = None
        self._create_temp_workdir()

    def __del__(self):
        if os.path.exists(self.temp_workdir):
            shutil.rmtree(self.temp_workdir)

    def _create_temp_workdir(self):
        try:
            self.temp_workdir = tempfile.mkdtemp()
            self.style_path = os.path.join(self.temp_workdir, "style.css")
            with open(self.style_path, "wt") as f:
                print("@page {", file=f)
                print("    width: 27cm;", file=f)
                print("    background: white;", file=f)
                print("}", file=f)
        except OSError as e:
            raise ScreenshotError(
                f"error while creating weasyprint stylesheet file: {e}"
            ) from e

    def convert(self, input_file_path: str, output_file_path: str, dpi: int):
        cmd = f"weasyprint -r {dpi} -s {self.style_path} {input_file_path} {output_file_path}"

        exit_code, _, output = run_shell_cmd(cmd, timeout_sec=10)
        output = output.decode(errors="replace")
        if exit_code != 0:
            raise ScreenshotError(
                f"got bad exit code {exit_code} while converting {input_file_path} to {output_file_path}: \n{output}"
            )
