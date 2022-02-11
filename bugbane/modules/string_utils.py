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

from typing import List

import logging

log = logging.getLogger(__name__)

from bugbane.modules.format import zfill_to_collection_size


def is_glob_mask(text: str) -> bool:
    """
    Checks whether text contains mathing symbols usable with glob.glob()
    """
    symbols = ["*", "?"]
    return any(s in text for s in symbols)


def replace_part_in_str_list(
    cmds: List[str],
    what: str,
    with_what: str,
    num_repl: int,
    start: int,
    end: int = None,
) -> None:
    """
    cmds: list of commands to be modified
    what: what to search
    with_what: replacement for matching substrings
    num_repl: number of replacements within one command (-1 = replace all occurrences)
    start: index of the first cmd to be processed in collection
    end: index of the last cmd to be processed in collection

    If end is None, replace only one item at index start.
    with_what may include $i which will be replaced with fuzzer number starting from 1
    """

    log.trace(
        "want to replace '%s' with '%s' in cmds[ %d .. %d ]",
        what,
        with_what,
        start,
        end or 0,
    )

    if start >= len(cmds):
        start = len(cmds) - 1

    if end is None:
        end = start

    if end >= len(cmds):
        end = len(cmds) - 1

    if end < start:
        end = start

    log.trace("               corrected indexes: cmds[ %d .. %d ]", start, end)

    _check_ranges(len(cmds), start, end)

    for i in range(start, end + 1):
        if with_what:
            repl = with_what.replace("$i", zfill_to_collection_size(i + 1, len(cmds)))
        else:
            repl = ""
        cmds[i] = cmds[i].replace(what, repl, num_repl)


def _check_ranges(collection_size: int, start: int, end: int):
    if start < 0 or start >= collection_size:
        raise IndexError(
            f"start={start} is out of bounds for sequence of size {collection_size}"
        )

    if end < start or end >= collection_size:
        raise IndexError(
            f"end={end} is out of bounds for sequence of size {collection_size} or is less than start index {start}"
        )
