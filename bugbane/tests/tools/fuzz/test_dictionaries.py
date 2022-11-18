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

from typing import Set
from io import StringIO

import pytest
from pytest_mock import MockerFixture

from bugbane.modules.fuzz_dict.dict_processor import (
    DictProcessor,
    DictProcessorException,
)

MOCK_GLOB = "bugbane.modules.fuzz_dict.dict_processor.glob.glob"
MOCK_OPEN = "bugbane.modules.fuzz_dict.dict_processor.open"
MOCK_FILE_UTILS_NONE_ON_BAD = "bugbane.modules.file_utils.none_on_bad_nonempty_file"


def test_init():
    d = DictProcessor()
    assert d.tokens is not None
    assert len(d.tokens) == 0
    assert isinstance(d.tokens, Set)


def test_add_from_lines():
    lines = [
        r'#"comment1"',
        r'"token1"',
        r'"\xFF\x00"',
        r'"\x00"',
        r"",
        r"# comment2",
    ]

    d = DictProcessor()
    d.add_from_lines(lines)
    assert len(d.tokens) == 3
    assert isinstance(d.tokens, Set)
    assert d.get_tokens() == [
        r'"\x00"',
        r'"\xFF\x00"',
        r'"token1"',
    ]

    lines2 = [
        r'"token2"',
        r'"token1"',
    ]
    d.add_from_lines(lines2)
    assert len(d.tokens) == 4
    assert d.get_tokens() == [
        r'"\x00"',
        r'"\xFF\x00"',
        r'"token1"',
        r'"token2"',
    ]


def test_clear():
    lines = [
        r"# comment",
        r'"token"',
        r'"\xFF\x00"',
        r'"\x00"',
    ]

    d = DictProcessor()
    d.add_from_lines(lines)
    assert len(d.tokens) == 3

    d.clear_tokens()
    assert d.tokens is not None
    assert len(d.tokens) == 0
    assert isinstance(d.tokens, Set)
    assert d.get_tokens() == []


def test_add_from_directory(mocker: MockerFixture):
    files = {
        "1.dict": '# comment\n# comment2\n"token1"\n"token2" # comment after token',
        "something": '# comment\n# comment2\n"token4"\n"token5"',
        "2.dict": '# comment\n# comment2\n"token2"\ntoken_name="token3"',
        "3.dict": "# only comment here\n",
    }

    mocker.patch(
        MOCK_GLOB,
        return_value=[fname for fname in files if fname.endswith(".dict")],
    )
    mocker.patch(MOCK_OPEN, lambda v, mode, encoding: StringIO(files[v]))
    mocker.patch(MOCK_FILE_UTILS_NONE_ON_BAD, lambda s: s)

    d = DictProcessor()
    d.add_from_directory(".")
    assert d.tokens is not None
    assert len(d.tokens) == 3
    assert isinstance(d.tokens, Set)
    assert d.get_tokens() == [
        '"token1"',
        '"token2"',
        '"token3"',
    ]


def test_add_from_file_bad(mocker: MockerFixture):
    mocker.patch(MOCK_FILE_UTILS_NONE_ON_BAD, return_value=None)
    d = DictProcessor()
    with pytest.raises(DictProcessorException):
        d.add_from_file("nonexistent")


def test_add_from_file_read_error(mocker: MockerFixture):
    mocker.patch(MOCK_FILE_UTILS_NONE_ON_BAD, lambda s: s)

    def new_open(path, mode, encoding):
        raise OSError("test")

    mocker.patch(MOCK_OPEN, new_open)
    d = DictProcessor()
    with pytest.raises(DictProcessorException):
        d.add_from_file("nonexistent")


def test_save_to_file(mocker: MockerFixture):
    mock_open = mocker.patch(MOCK_OPEN)

    d = DictProcessor()
    d.tokens = {'"tok3"', '"tok1"', '"tok2"'}
    d.save_to_file("nonexistent")

    mock_open().__enter__().writelines.assert_called_once_with(
        ['"tok1"\n', '"tok2"\n', '"tok3"\n']
    )


def test_save_to_file_write_error(mocker: MockerFixture):
    def new_open(path, mode, encoding):
        raise OSError("test")

    mocker.patch(MOCK_OPEN, new_open)

    d = DictProcessor()
    d.tokens = {'"tok3"', '"tok1"', '"tok2"'}
    with pytest.raises(DictProcessorException):
        d.save_to_file("nonexistent")
