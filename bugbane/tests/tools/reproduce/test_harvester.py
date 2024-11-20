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
from typing import Any, Dict

from bugbane.tools.reproduce import harvester
from bugbane.tools.reproduce.harvester import IssueCard
from bugbane.tools.reproduce.verdict import Verdict

import pytest


@pytest.mark.parametrize(
    "path, mask, expected",
    [
        # fmt: off
        ("target/date/bb_results.json", "target/*/bug_samples/*", "target/date/bug_samples"),
        ("target/date/bb_results.json", "target/*/bugs/files/*", "target/date/bugs/files"),
        ("target/date/bb_results.json", "target/*/*", "target/date"),
        ("/target/date/bb_results.json", "/target/*/*", "/target/date"),
        # fmt: on
    ],
)
def test_restore_path_by_mask(path: str, mask: str, expected: str) -> None:
    assert harvester.samples_dir_for_results_file(path, mask) == expected


@pytest.mark.parametrize(
    "reproduce_cmd, expected",
    [
        # fmt: off
        ('ubsan/app "./out/target/crashes/id:000000,sig:06,sync:m1,src:000000"', "@@"),
        ('./app --file "./out/target/crashes/id:000000,sig:06,sync:m1,src:000000"', "--file @@"),
        ('myapp < "./out/target/crashes/id:000000,sig:06,sync:m1,src:000000"', ""),
        ('myapp "./artifacts/crash-1234567890"', "@@"),
        ("""timeout --kill-after 9s -s SIGINT 2s gdb --ex 'r "artifacts/crash-57700c512968964cfaaea5932b3747cd99884f80"' --ex "q" ./asan/app 0</dev/null""", "@@"),
        ("""gdb --ex 'r < "out/target/crashes/id:000000,sig:06,sync:m1,src:000000"' --ex "q" ./asan/app 0</dev/null""", ""),
        # fmt: on
    ],
)
def test_restore_run_args(reproduce_cmd: str, expected: str) -> None:
    assert harvester.restore_run_args(reproduce_cmd) == expected


@pytest.mark.parametrize(
    "issue_card_dict, expected",
    [
        (  # a good case
            {
                "reproduce_cmd": "ubsan/app < crash1",
                "reproduce_env": "LANG=C.UTF-8",
                "output": "hello",
                "binary": "ubsan/app",
                "sample": "crash1",
                "file": "src.cpp",
                "line": 678,
                "verdict": "CRASH_UBSAN",
                "title": "Some Issue Title",
                "is_old": True,
                "is_extra": False,
            },
            IssueCard(
                reproduce_cmd="ubsan/app < crash1",
                reproduce_env="LANG=C.UTF-8",
                output="hello",
                binary="ubsan/app",
                sample="crash1",
                file="src.cpp",
                line=678,
                verdict=Verdict.CRASH_UBSAN,
                title="Some Issue Title",
                is_old=True,
                is_extra=False,
            ),
        ),
        (  # some fields missing (i.e. reading format from the older bugbane version)
            {
                "reproduce_cmd": "ubsan/app < crash1",
                "reproduce_env": "",
                "output": "hello",
                "binary": "ubsan/app",
                "sample": "crash1",
                "file": "src.cpp",
                "verdict": "CRASH_UBSAN",
                "title": "Some Issue Title",
            },
            IssueCard(
                reproduce_cmd="ubsan/app < crash1",
                reproduce_env="",
                output="hello",
                binary="ubsan/app",
                sample="crash1",
                file="src.cpp",
                line=None,
                verdict=Verdict.CRASH_UBSAN,
                title="Some Issue Title",
                is_old=None,
                is_extra=None,
            ),
        ),
        (  # extra fields (i.e. reading format from the future bugbane version)
            {
                "reproduce_cmd": "ubsan/app < crash1",
                "reproduce_env": "LANG=C.UTF-8",
                "output": "hello",
                "binary": "ubsan/app",
                "sample": "crash1",
                "some unknown field 1": 123,
                "file": "src.cpp",
                "line": 678,
                "verdict": "CRASH_UBSAN",
                "title": "Some Issue Title",
                "is_old": True,
                "is_extra": False,
                "some unknown field 2": "value",
            },
            IssueCard(
                reproduce_cmd="ubsan/app < crash1",
                reproduce_env="LANG=C.UTF-8",
                output="hello",
                binary="ubsan/app",
                sample="crash1",
                file="src.cpp",
                line=678,
                verdict=Verdict.CRASH_UBSAN,
                title="Some Issue Title",
                is_old=True,
                is_extra=False,
            ),
        ),
    ],
)
def test_dict_to_issue_cards(issue_card_dict: Dict[str, Any], expected: str) -> None:
    result = harvester.Harvester.dict_to_issue_cards([issue_card_dict])
    assert len(result) == 1
    assert result[0] == expected
