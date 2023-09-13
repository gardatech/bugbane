# Copyright 2022-2023 Garda Technologies, LLC. All rights reserved.
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

from typing import Dict, List, Union

import os
import re
import shutil


class BugSampleSaverError(Exception):
    """Exception class for errors that happen in BugSampleSaver class."""


class BugSampleSaver:
    """
    Class responsible for saving crash/hang samples.
    Copies samples specified in issue_cards of bugbane fuzz results dictionary.
    Updates issue_cards with copied sample names.
    Raises `BugSampleSaverError` in case of errors.
    Empty issue_cards field in results dictionary is not considered an error.
    """

    def __init__(self, max_file_name_len: int):
        self.re_bad_filename_chars = re.compile(r"[^_0-9a-z]+")
        self.re_multiple_underscores = re.compile(r"_{2,}")
        self.max_file_name_len = max_file_name_len - 5
        if self.max_file_name_len < 10:
            raise BugSampleSaverError("too low value for max file name length, use 15 or more")

    def save_bug_samples(
        self,
        results: Dict[str, List[Dict[str, Union[str, int, float]]]],
        output_dir: str,
    ) -> None:
        """
        Copy bug samples to separate directory,
        update input `results` dict with new names.
        """
        self.create_output_dir(output_dir)
        for card in results["issue_cards"]:
            self.save_bug_sample(card, output_dir)

    def create_output_dir(self, output_dir: str) -> None:
        """Create output directory if it doesn't exist."""
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
        except OSError as e:
            raise BugSampleSaverError(
                f"wasn't able to create output directory '{output_dir}'"
            ) from e

    def save_bug_sample(
        self, issue_card: Dict[str, Union[str, float, int]], output_dir: str
    ) -> None:
        """
        Save one crash/hang sample to `output_dir`.
        Change saved sample name in input `issue_card`.
        """
        try:
            sample_path = issue_card["sample"]
            title = issue_card["title"]
        except KeyError as e:
            raise BugSampleSaverError(
                f"malformed issue_card read from results file (missing key: {e})"
            ) from e
        save_name = self.title_to_sample_name(str(title))
        save_path = os.path.join(output_dir, save_name)

        save_path = self.get_next_free_file_name(save_path)

        try:
            shutil.copyfile(str(sample_path), save_path)
        except OSError as e:
            raise BugSampleSaverError(
                f"wasn't able to copy file '{sample_path}' to '{save_path}'"
            ) from e

        issue_card["sample"] = save_name

    def title_to_sample_name(self, issue_title: str) -> str:
        """
        Convert issue title to sample name.
        Result consists only of simple characters (no colons, commas, etc).
        """
        lowered_title = issue_title.lower()
        filtered = self.re_bad_filename_chars.sub("_", lowered_title)
        normalized = self.re_multiple_underscores.sub("_", filtered)
        shortened = self.shorten_sample_name(
            normalized, new_mid_part="_-_-_", max_len=self.max_file_name_len
        )
        return shortened

    @staticmethod
    def shorten_sample_name(sample_name: str, new_mid_part: str, max_len: int) -> str:
        """
        Return shortened variant of the `sample_name` string by replacing the middle part
        of the `sample_name` with `new_mid_part`.
        If `sample_name` is already not longer than `max_len`, then it's returned without
        changes.
        """
        if len(sample_name) <= max_len:
            return sample_name

        num_orig_chars = max_len - len(new_mid_part)

        half, offset = divmod(num_orig_chars, 2)
        return sample_name[: half + offset] + new_mid_part + sample_name[-half:]

    @staticmethod
    def get_next_free_file_name(wanted_path: str) -> str:
        """
        Generate the next available file name if `wanted_path` already exists.
        """
        number = 1
        orig_wanted_path = wanted_path
        while os.path.exists(wanted_path):
            wanted_path = orig_wanted_path + "%04d" % number
        return wanted_path
