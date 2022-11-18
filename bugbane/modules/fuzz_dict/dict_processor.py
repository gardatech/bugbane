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

from typing import List, Set

import os
import glob

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules import file_utils


class DictProcessorException(Exception):
    """Class representing errors in DictProcessor."""


class DictProcessor:
    """
    Class for loading and merging AFL-like dictionaries.
    Raises DictProcessorException in case of errors.
    """

    def __init__(self):
        self.tokens: Set[str] = set()

    def clear_tokens(self) -> None:
        """
        Remove all tokens from instance variables.
        """
        self.tokens.clear()

    def add_from_directory(self, dict_dir_path: str, mask: str = "*.dict") -> None:
        """
        Load and merge dictionaries from specified directory.
        Only files that match given glob mask will be loaded.
        """

        fpaths = glob.glob(os.path.join(dict_dir_path, mask))
        for fpath in sorted(fpaths):
            self.add_from_file(fpath)

    def add_from_file(self, dict_file_path: str) -> None:
        """Load dictionary tokens from file and store them to instance variables."""
        lines = self._read_lines_from_file(dict_file_path)
        self.add_from_lines(lines)

    def _read_lines_from_file(self, file_path: str) -> List[str]:
        """
        Read all lines from file in UTF-8 encoding. Return list of lines.
        Raise DictProcessorException in case of errors or bad file.
        """

        path = file_utils.none_on_bad_nonempty_file(file_path)
        if not path:
            raise DictProcessorException(
                f"File {file_path} is empty, not readable or doesn't exist"
            )

        try:
            with open(file_path, "rt", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            raise DictProcessorException(f"Wasn't able to read file {file_path}") from e

        return lines

    def add_from_lines(self, lines: List[str]) -> None:
        """
        Load dictionary tokens from input lines (read from dictionary file).
        Add tokens to instance variables.
        """
        tokens = self._extract_tokens_from_lines(lines)
        self.tokens.update(tokens)

    def _extract_tokens_from_lines(self, lines: List[str]) -> Set[str]:
        """
        Load tokens from input lines previously read from file.
        Skip comments and empty lines.
        Return tokens as set of strings.
        """

        tokens: Set[str] = set()

        for line in lines:
            t = self._extract_token_from_one_line(line)
            if not self._is_token_valid(t):
                if t:
                    log.warning("invalid dictionary token skipped: %s", line)
                continue
            tokens.add(t)

        return tokens

    def _extract_token_from_one_line(self, line: str) -> str:
        """
        If line is empty or starts with comment, return empty string.
        Otherwise, remove optional token name and return extracted token.
        """

        t = line.strip()
        if not t or t.startswith("#"):
            return ""

        # remove comment after token
        if "#" in t:
            t = t.split("#")[0]

        if "=" not in t:
            return t

        t = t.split("=")[1]
        return t.strip()

    def _is_token_valid(self, token: str) -> bool:
        """
        Return True if token is not empty and is quoted with double quotes.
        Return False otherwise.
        """
        if not token:
            return False

        if len(token) < 3:  # quotes + at least one symbol
            return False

        return token.startswith('"') and token.endswith('"')

    def get_tokens(self) -> List[str]:
        """
        Return dictionary tokens currently saved in instance variables.
        Result is sorted list of strings.
        """
        return sorted(self.tokens)

    def save_to_file(self, output_dict_file_path: str) -> None:
        """
        Save dictionary tokens currently saved in instance variables
        to specified file.
        """

        try:
            with open(output_dict_file_path, "wt", encoding="utf-8") as f:
                print(
                    "# this dictionary was automatically generated with BugBane", file=f
                )
                # TODO: generator expression instead of list comprehension (how to test?)
                f.writelines([s + "\n" for s in self.get_tokens()])
        except OSError as e:
            raise DictProcessorException(
                f"Wasn't able to write tokens fo file {output_dict_file_path}"
            ) from e
