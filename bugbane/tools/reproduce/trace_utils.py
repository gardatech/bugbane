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

from typing import Optional, Tuple

import os
import re
import logging

from collections import Counter

log = logging.getLogger(__name__)


def remove_column_from_location(location: Optional[str]) -> Optional[str]:
    if not location:
        return location

    re_line_column = re.compile(r"^(.*?):(\d+)(?::\d+)?$")
    return re.sub(re_line_column, r"\1:\2", location)


def anonymize_run_string(t: str) -> str:
    """
    Generalizes hex addresses, some sanitizer error numbers, values in "()" brackets.
    Use with output, location or issue title
    """

    if not t:
        return t

    re_hex_addr = re.compile(r"0[xX][0-9a-fA-F]{1,}")
    re_sanitizer_error_id = re.compile(r"^==(\d+)==([^=])", re.MULTILINE)
    re_register = re.compile(r" sp 0xADDRESS T\d+\)$", re.MULTILINE)
    re_sh_segfault = re.compile(
        r"^sh: line \d+:\s*\d+\s*(?:Segmentation fault|Aborted).*$", re.MULTILINE
    )
    re_bracketed_values = re.compile(r"(\(.*?\))", re.MULTILINE)
    re_multiple_spaces = re.compile(r"( {2,})")

    t = re.sub(re_hex_addr, "0xADDRESS", t)
    t = re.sub(re_register, " sp 0xADDRESS T<NUM>)", t)
    t = re.sub(re_sanitizer_error_id, r"==1==\2", t)
    t = re.sub(re_sh_segfault, "Segmentation fault", t)
    t = re.sub(re_bracketed_values, " ", t)
    t = re.sub(re_multiple_spaces, " ", t)

    return t


def get_hang_location(output: str, src_path: Optional[str]) -> Optional[str]:
    """
    Extracts from output and returns hang location in form of "at /path/to/file.cpp:22"
        or "in func at /path/to/file.cpp:22"

    Use on output of command like this:
    ```
    env LANG=C timeout --kill-after 9s -s SIGINT 2s \
        gdb -q --ex 'r < "path/to/hang/file"' \
            --ex "echo <HANG_START>\n" \
            --ex "step 1" --ex "info line" \
            --ex "step 11" --ex "info line" \
            --ex "step 111" --ex "info line" \
            --ex "step 1111" --ex "info line" \
            --ex "step 111" --ex "info line" \
            --ex "echo <HANG_END>\n" \
            --ex "q" \
            ./tested_app 0</dev/null'
    ```
    """

    if not output:
        return None

    result = get_golang_crash_or_hang_location(output, src_path)
    if result is not None:
        return result

    if "<HANG_START>" not in output:
        return None

    re_minimal_hang_location = re.compile(
        r".*^Line\s+(\d+)\s+of\s+\"?(.*)\"\s+starts", re.MULTILINE | re.DOTALL
    )  # groups: 1=line, 2=file
    re_hang_locatin_with_func = re.compile(
        r"^Line\s+(\d+)\s+of\s+\"?(.*?)\"?\s+starts.*?\<(.*?)(?:\>|\()",
        re.MULTILINE | re.DOTALL,
    )  # groups: 1=line, 2=file, 3=func

    locations = re.findall(re_hang_locatin_with_func, output)
    if not locations:
        locations = re.findall(re_minimal_hang_location, output)
    log.trace("locations: %s", locations)
    if not locations:
        log.debug("wasn't able to determine hang location")
        return None

    counter = Counter(locations)
    top = counter.most_common(1)  # [(matched_groups,), count]
    top = top[0][0]
    result = f"at {top[1]}:{top[0]}"
    if len(top) > 2:
        result = f"in {top[2]} {result}"

    return result


def get_crash_location(output: str, src_path: Optional[str] = None) -> Optional[str]:
    """
    Return first user code location from
    run results (produced by either sanitizers or gdb)
    """

    t = output
    result = get_golang_crash_or_hang_location(t, src_path)
    if result is not None:
        return result

    result = get_gdb_crash_location(t, src_path)
    if result is not None:
        return result

    # no gdb output detected
    log.debug("no gdb stacktrace found")

    result = get_sanitizer_crash_location(t)
    if result is not None:
        return result

    log.debug("wasn't able to determine crash location")
    return None


def get_golang_crash_or_hang_location(
    output: str, src_path: Optional[str] = None
) -> Optional[str]:
    """
    Find first user code in golang stack trace.
    If user code can't be found, return first location in stack trace.
    If it can't be found, return None
    """
    src_path = src_path or ""
    re_go_stacktrace = re.compile(
        r"^(?:.*/)?(.*?)\(.*?\)$\s+(.*?\.go:\d+)\s+.*?$", re.MULTILINE
    )
    # groups: 1=func 2=file+line

    match = re_go_stacktrace.search(output)
    log.trace("first match: %s", match)
    if not match:
        return None

    for m in re_go_stacktrace.finditer(output):
        log.trace("match in loop: %s", m)
        if m.group(2).startswith(src_path):
            match = m
            break

    func_name = match.group(1)
    file_path = match.group(2)

    location = "in " + func_name + " at " + file_path
    log.debug("golang location: %s", location)
    return location


def get_gdb_crash_location(output: str, src_path: Optional[str] = None) -> str:
    """
    output: application run output
    src_path: path to sources when the application was built; directory may not exist
    """

    t = output

    re_check_gdb = re.compile(r".*^#\d+\s+0[xX].*?in", re.MULTILINE | re.DOTALL)

    if re.match(re_check_gdb, t) is None:
        return None

    re_gdb_location = re.compile(
        r"^#\d+\s+0[xX][\S]{1,}\s+(in\s+.*\s+(?:at|from).*?$)", re.MULTILINE
    )
    locations = re.findall(re_gdb_location, t)

    if not locations:
        return None

    log.verbose3(
        "GDB STACKTRACE FOUND, location candidates:\n\t" + "\n\t".join(locations)
    )

    # return first src location
    for location in locations:
        gdb_check_src_location = r"in\s+(.*?)\s+at\s+("
        if src_path:
            gdb_check_src_location += src_path
        gdb_check_src_location += r".*?)$"
        log.debug("gdb_check_src_location: %s", gdb_check_src_location)
        re_gdb_check_src_location = re.compile(gdb_check_src_location)

        if re.match(re_gdb_check_src_location, location):
            return location

    # no src locations, return topmost location of the stack trace
    return locations[0]


def get_sanitizer_crash_location(output: str) -> str:
    t = output

    # ubsan/cfisan
    re_sanitizer_location = re.compile(
        r".*SUMMARY:\s+(\S+Sanitizer):\s+(\S+)\s+(.*?)\s+in\s*?$",
        re.MULTILINE | re.DOTALL,
    )
    location = re.match(re_sanitizer_location, t)
    if location:
        # 1 = sanitizer name (UndefinedBehaviorSanitizer)
        # 2 = issue type (undefined-behavior)
        # 3 = file, line, column (/src/src/fuzzable_app.cpp:29:31)
        return "at " + location.group(3)

    # asan
    re_asan_location = re.compile(
        r".*SUMMARY:\s+AddressSanitizer:\s+(\S+)\s+(.*?)\s+in\s+(.*?)\s*$",
        re.MULTILINE | re.DOTALL,
    )
    location = re.match(re_asan_location, t)
    if location:
        # 1 = issue type (global-buffer-overflow)
        # 2 = file, line, column (/src/src/fuzzable_app.cpp:38:22)
        # 3 = function name (fuzz)
        issue_type = location.group(1)
        if issue_type == "SEGV":
            return "in " + location.group(3) + " at " + location.group(2)

        return issue_type + " in " + location.group(3) + " at " + location.group(2)

    return None


def location_to_file_line(location: str) -> Tuple[str, Optional[int]]:
    """
    Extract file and line number from location
    Return tuple (file, line)
    If line number cannot be extracted return (location, None)
    """

    if not location:
        return (location, None)

    pos = location.rfind(":")
    if pos == -1:
        return (location, None)

    file = location[:pos]

    # Crash in just_abort at /src/src/../include/funcs.h:12
    # AddressSanitizer: global-buffer-overflow in fuzz at /src/src/fuzzable_app.cpp:30
    file_split = file.split(" ")
    if len(file_split) > 1:
        file = file_split[-1]

    line = location[pos + 1 :]
    if line.isnumeric():
        if os.path.isfile(file):
            return (os.path.normpath(file), int(line))

        return (file, int(line))

    return (location, None)
