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

from typing import List, Optional

import os
import sys
import json
from io import SEEK_END

import logging

log = logging.getLogger(__name__)


def dump_dict_as_json(filepath: Optional[str], result: dict):
    need_print = True

    if filepath:
        if save_dict_to_json_file(result, filepath):
            log.verbose2("Saved JSON results to %s", filepath)
            need_print = False
        else:
            log.error("wasn't able to save JSON results to file %s", filepath)

    if need_print:
        print_dict_as_json(result)


def save_dict_to_json_file(d: dict, path: str) -> bool:
    """Save dict to file in JSON format. Return True on success"""
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(d, file, ensure_ascii=False, indent=4)
        return True
    except OSError:
        return False


def print_dict_as_json(d: dict):
    """Dump dictionary to stdout in JSON format"""
    json.dump(d, sys.stdout, ensure_ascii=False, indent=4)


def make_relative_path(path: str, num_components: int):
    """
    Returns last num_components path parts joined via os.path.join
    """
    normpath = os.path.normpath(path)
    parts = normpath.split(os.path.sep)[-num_components:]
    if len(parts) < 2:
        return parts[0]

    return os.path.join(*parts)


def none_on_bad_file(*path_components: str) -> Optional[str]:
    """
    If file exists and is read accessible,
    return path joined from path_components.

    Return None otherwise
    """

    path = none_on_bad_path(*path_components)

    if path is None:
        return None

    if not os.path.isfile(path):
        return None

    if not os.access(path, os.R_OK):
        return None

    return path


def none_on_bad_nonempty_file(*path_components: str) -> Optional[str]:
    """
    If file exists, read accessible and is not empty,
    return path joined from path_components.

    Return None otherwise
    """

    path = none_on_bad_file(*path_components)

    if path is None:
        return None

    if not os.path.getsize(path):
        return None

    return path


def none_on_bad_empty_file(*path_components: str) -> Optional[str]:
    """
    If file exists, read accessible and is empty,
    return path joined from path_components.

    Return None otherwise
    """

    path = none_on_bad_file(*path_components)

    if path is None:
        return None

    if os.path.getsize(path):
        return None

    return path


def none_on_bad_dir(*path_components: str) -> Optional[str]:
    """
    If directory exists and is read accessible,
    return path joined from path_components.

    Return None otherwise
    """

    path = none_on_bad_path(*path_components)

    if path is None:
        return None

    if not os.path.isdir(path):
        return None

    if not os.access(path, os.R_OK):
        return None

    return path


def none_on_bad_empty_dir(*path_components: str) -> Optional[str]:
    """
    If directory exists, read accessible and is empty,
    return path joined from path_components.

    Return None otherwise
    """

    path = none_on_bad_dir(*path_components)

    if path is None:
        return None

    if os.listdir(path):
        return None

    return path


def none_on_bad_nonempty_dir(*path_components: str) -> Optional[str]:
    """
    If directory exists, read accessible and is not empty,
    return path joined from path_components.

    Return None otherwise
    """

    path = none_on_bad_dir(*path_components)

    if path is None:
        return None

    if not os.listdir(path):
        return None

    return path


def none_on_bad_path(*path_components: str) -> Optional[str]:
    """
    Construct path from path_components via os.path.join.

    Return None if:
        1. path is None or empty
        2. path doesn't exist
        3. path is not readable

    Return path otherwise
    """

    if not path_components:
        return None

    if len(path_components) < 2:
        path = path_components[0]
    else:
        path = os.path.join(*path_components)

    if not os.path.exists(path):
        return None

    if not os.access(path, os.R_OK):
        return None

    return path


def read_last_lines(
    filepath: str, num_lines: int, expected_line_size: int
) -> List[str]:
    """
    Reads approximately `num_lines * expected_line_size` bytes from the end of file,
    returns stripped read lines as list of strings
    """

    bytes_to_read = (num_lines + 1) * expected_line_size
    bytes_to_read = bytes_to_read or 1

    with open(filepath, "rb") as f:
        if os.path.getsize(filepath) > bytes_to_read:
            f.seek(-bytes_to_read, SEEK_END)
        lines = f.readlines()[-num_lines:]

    return list(map(lambda x: x.decode("utf-8").strip(), lines))
