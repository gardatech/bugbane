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
Screenshot tool
"""

import sys
import shutil

from .args import parse_args

from bugbane.modules.log import get_first_logger

from .factory import ScreenshotMakerFactory
from .screenshot import ScreenshotError


def main(argv=None):
    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_first_logger(__name__, args.verbose)

    if args.screener == "pango":
        if shutil.which("pango-view") is None:
            log.error("pango-view wasn't found in PATH")
            return 1

        if shutil.which("ansifilter") is None:
            log.warning("ansifilter wasn't found in PATH, expect bad screenshots")

    try:
        screener = ScreenshotMakerFactory.create(args.screener)
        log.verbose1("Using screenshot maker: %s", screener.__class__.__name__)
    except ValueError as e:
        log.error("Wasn't able to create screenshot maker: %s", e)
        return 1

    try:
        screener.convert(args.input, args.output, args.dpi)
    except ScreenshotError as e:
        log.error("Wasn't able to create image: %s", e)
        return 1

    return 0
