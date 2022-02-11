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

from typing import Optional

import os
import glob
import logging

log = logging.getLogger(__name__)

from bugbane.modules.file_utils import make_relative_path
from .emitter import Emitter, EmitterError, TemplateRenderError
from ..screenshot.screenshot import ScreenshotMaker


class EmitterWithScreenshots(Emitter):
    def __init__(self):
        super().__init__()
        self.ansi_screenshot_maker: Optional[ScreenshotMaker] = None
        self.html_screenshot_maker: Optional[ScreenshotMaker] = None
        self.screehsnot_paths: dict[str, str] = {}

    def set_ansi_screenshot_maker(self, screener: ScreenshotMaker):
        """
        Sets instance variable self.ansi_screenshot_maker to screenshot_maker
        """
        self.ansi_screenshot_maker = screener

    def set_html_screenshot_maker(self, screener: ScreenshotMaker):
        """
        Sets instance variable self.html_screenshot_maker to screenshot_maker
        """
        self.html_screenshot_maker = screener

    def make_screenshots(self, output_directory: str, fuzzer_has_stats: bool):
        """
        Removes all PNG files from output_directory.
        Creates screenshots that should be rendered to report files,
        saves screenshot files to output_directory.
        """

        if self.suite is None:
            raise EmitterError("fuzzing suite not set")

        try:
            if os.path.exists(output_directory):
                self.delete_existing_screenshots(output_directory)
            else:
                os.makedirs(output_directory)
        except OSError as e:
            raise EmitterError(
                f"while deleting existing screenshots in direcotry {output_directory}: {e}"
            ) from e

        dumps = self.make_ansi_screenshots(output_directory)

        if fuzzer_has_stats:
            self.screehsnot_paths = {
                "screen_stats": dumps[0],
                "screen_fuzzers": dumps[1:],
            }
        else:
            self.screehsnot_paths = {
                "screen_stats": None,
                "screen_fuzzers": dumps,
            }

        coverage = self.make_html_screenshots(output_directory)
        self.screehsnot_paths.update({"screen_coverage": coverage})

    def delete_existing_screenshots(self, output_directory: str):
        pngs = glob.glob(os.path.join(output_directory, "*.png"))
        log.trace("going to delete pngs=%s", pngs)
        for png in pngs:
            os.remove(png)

    def make_ansi_screenshots(self, output_directory: str):
        if self.suite.screen_dumps_dir is None:
            return

        if self.ansi_screenshot_maker is None:
            raise TemplateRenderError("ansi screenshot maker not set")

        namestart = "screen"
        pattern = os.path.join(self.suite.screen_dumps_dir, namestart + "*")
        screens = glob.glob(pattern)
        screens = sorted(
            screens, key=lambda p: int(os.path.basename(p).replace(namestart, ""))
        )
        log.trace("screens=%s", screens)

        outpaths = []
        for screen in screens:
            outpath = os.path.join(output_directory, os.path.basename(screen) + ".png")
            log.trace("converting %s to %s", screen, outpath)
            self.ansi_screenshot_maker.convert(screen, outpath, 128)
            outpaths.append(
                make_relative_path(outpath, 2)
            )  # report.md uses relative paths to images

        return outpaths

    def make_html_screenshots(self, output_directory: str) -> Optional[str]:
        """
        Make screenshot of index.html file in self.overage_report_path dir.
        Return path relative to output directory suitable for use in report.md
        """
        # TODO: for LLVM there may be multiple coverage reports
        # TODO: for GO it's easier to convert text report or use selenium for js

        if self.suite.coverage_report_path is None:
            return None

        if self.html_screenshot_maker is None:
            raise TemplateRenderError("html screenshot maker not set")

        coverage_html = os.path.join(self.suite.coverage_report_path, "index.html")
        log.trace("coverage_html=%s", coverage_html)
        outpath = os.path.join(output_directory, "coverage.png")
        self.html_screenshot_maker.convert(coverage_html, outpath, 128)
        return make_relative_path(outpath, 2)  # report.md uses relative paths to images
