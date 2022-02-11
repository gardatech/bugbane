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
import tempfile
from io import BytesIO
from pytest_mock import MockerFixture

from bugbane.modules import file_utils

MOCK_FILE_UTILS_OPEN = "bugbane.modules.file_utils.open"
MOCK_FILE_UTILS_OS_PATH_GETSIZE = "bugbane.modules.file_utils.os.path.getsize"


def test_relative_path():
    path = "/mnt/output/screenshots/screen9.png"
    assert file_utils.make_relative_path(path, 2) == "screenshots/screen9.png"
    assert file_utils.make_relative_path(path, 3) == "output/screenshots/screen9.png"


def test_none_on_bad_nonempty_file():
    assert file_utils.none_on_bad_nonempty_file(tempfile.mktemp()) is None
    assert file_utils.none_on_bad_nonempty_file(__file__) is not None
    assert (
        file_utils.none_on_bad_nonempty_file(
            os.path.join(os.path.dirname(__file__), "..", "__init__.py")
        )
        is None
    )


def test_none_on_bad_nonempty_dir():
    assert file_utils.none_on_bad_nonempty_dir(tempfile.mktemp()) is None
    assert file_utils.none_on_bad_nonempty_dir(os.path.dirname(__file__)) is not None


def test_none_on_bad_empty_file():
    assert file_utils.none_on_bad_empty_file(tempfile.mktemp()) is None
    assert file_utils.none_on_bad_empty_file(__file__) is None
    assert (
        file_utils.none_on_bad_empty_file(
            os.path.join(os.path.dirname(__file__), "..", "__init__.py")
        )
        is not None
    )


def test_none_on_bad_empty_dir():
    assert file_utils.none_on_bad_empty_dir(tempfile.mktemp()) is None
    assert file_utils.none_on_bad_empty_dir(os.path.dirname(__file__)) is None


def test_read_last_lines(mocker: MockerFixture):
    log_contents = b"""2022/01/11 11:08:58 workers: 6, corpus: 731 (26m21s ago), crashers: 0, restarts: 1/9997, execs: 148459864 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:01 workers: 6, corpus: 731 (26m24s ago), crashers: 0, restarts: 1/9997, execs: 148518216 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:04 workers: 6, corpus: 731 (26m27s ago), crashers: 0, restarts: 1/9997, execs: 148570422 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:07 workers: 6, corpus: 731 (26m30s ago), crashers: 0, restarts: 1/9996, execs: 148622324 (19025/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:10 workers: 6, corpus: 731 (26m33s ago), crashers: 0, restarts: 1/9996, execs: 148682219 (19025/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:13 workers: 6, corpus: 731 (26m36s ago), crashers: 0, restarts: 1/9996, execs: 148743039 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:16 workers: 6, corpus: 731 (26m39s ago), crashers: 0, restarts: 1/9996, execs: 148800164 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:19 workers: 6, corpus: 731 (26m42s ago), crashers: 0, restarts: 1/9996, execs: 148862010 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:22 workers: 6, corpus: 731 (26m45s ago), crashers: 0, restarts: 1/9996, execs: 148922520 (19027/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:25 workers: 6, corpus: 731 (26m48s ago), crashers: 0, restarts: 1/9996, execs: 148981912 (19027/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:28 workers: 6, corpus: 731 (26m51s ago), crashers: 0, restarts: 1/9996, execs: 149042657 (19028/sec), cover: 825, uptime: 2h10m"""

    mocker.patch(MOCK_FILE_UTILS_OPEN, return_value=BytesIO(log_contents))
    mocker.patch(MOCK_FILE_UTILS_OS_PATH_GETSIZE, return_value=1966)
    expected = [
        "2022/01/11 11:09:22 workers: 6, corpus: 731 (26m45s ago), crashers: 0, restarts: 1/9996, execs: 148922520 (19027/sec), cover: 825, uptime: 2h10m",
        "2022/01/11 11:09:25 workers: 6, corpus: 731 (26m48s ago), crashers: 0, restarts: 1/9996, execs: 148981912 (19027/sec), cover: 825, uptime: 2h10m",
        "2022/01/11 11:09:28 workers: 6, corpus: 731 (26m51s ago), crashers: 0, restarts: 1/9996, execs: 149042657 (19028/sec), cover: 825, uptime: 2h10m",
    ]
    assert (
        file_utils.read_last_lines(
            "should/be/mocked", num_lines=3, expected_line_size=160
        )
        == expected
    )
