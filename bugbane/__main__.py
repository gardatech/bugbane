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

"""Common entry point for all the tools"""

import sys
import argparse

from bugbane.tools.corpus.main import main as corpus_main
from bugbane.tools.builder.main import main as builder_main
from bugbane.tools.fuzz.main import main as fuzz_main
from bugbane.tools.coverage.main import main as coverage_main
from bugbane.tools.reproduce.main import main as reproduce_main
from bugbane.tools.report.main import main as report_main
from bugbane.tools.send.main import main as send_main
from bugbane.tools.report.screenshot.main import main as screenshot_main

tool_mapping = {
    "corpus": corpus_main,
    "build": builder_main,
    "fuzz": fuzz_main,
    "coverage": coverage_main,
    "reproduce": reproduce_main,
    "report": report_main,
    "send": send_main,
    "screenshot": screenshot_main,
}


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) < 1:
        parser = argparse.ArgumentParser(
            description="%(prog)s - common entry point for all the BugBane tools",
            add_help=False,
        )
        parser.add_argument(
            "tool",
            help="name of the tool to run",
            choices=tool_mapping,
        )
        parser.add_argument(
            "arg", help="arguments for the tool", nargs=argparse.REMAINDER
        )
        parser.print_help()
        return 0

    tool = argv[0]
    args = argv[1:]
    if tool not in tool_mapping:
        print(
            f"ERROR: unknown tool '{tool}'. Tools supported:\n\t"
            + "\n\t".join(k for k in tool_mapping),
            file=sys.stderr,
        )
        return 1

    return tool_mapping[tool](args)


if __name__ == "__main__":
    sys.exit(main())
