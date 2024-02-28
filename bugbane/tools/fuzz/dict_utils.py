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

from typing import Optional

from bugbane.modules.fuzz_dict.dict_processor import (
    DictProcessor,
    DictProcessorException,
)


class DictMergeError(Exception):
    """Exception class for errors during merging of dictionaries."""


def merge_dictionaries_to_file(
    dict_dir: Optional[str], output_dict_path: str
) -> Optional[str]:
    """
    Merge dictionary files with extension ".dict" in specified directory `dict_dir`.
    Save merged dictionary as file at `output_dict_path`.
    Return `output_dict_path` on success.
    Return None if no dictionary was created due to missing input dictionaries.
    Raise DictMergeError on errors.
    """
    if not dict_dir:
        return None

    dict_processor = DictProcessor()
    try:
        dict_processor.add_from_directory(dict_dir)
        if len(dict_processor.get_tokens()) < 1:
            return None

        dict_processor.save_to_file(output_dict_path)
    except DictProcessorException as e:
        raise DictMergeError(f"Wasn't able to merge dictionaries: {e}") from e

    return output_dict_path
