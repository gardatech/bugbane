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

from typing import Optional, Tuple

import os
import re
from bugbane.modules.log import getLogger

from collections import Counter

log = getLogger(__name__)


def remove_column_from_location(location: Optional[str]) -> Optional[str]:
    """
    Remove column number from source location string.
    For strings like "path/to/file.cpp:20:56".
    Return str line "path/to/file.cpp:20" or
    input location if column info can not be removed."
    """
    if not location:
        return location

    re_line_column = re.compile(r"^(.*?):(\d+)(?::\d+)?$")
    return re.sub(re_line_column, r"\1:\2", location)


def post_process_location(location: Optional[str]) -> Optional[str]:
    """
    Remove column number from source location string.
    Normalize path: "a/b/../c" -> "a/c".
    Return input location if column couldn't be removed.
    """
    no_column_location = remove_column_from_location(location)
    if not no_column_location:
        return no_column_location
    return os.path.normpath(no_column_location)


def anonymize_run_string(t: Optional[str]) -> Optional[str]:
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

    result = get_dotnet_crash_or_hang_location(output, src_path)
    if result is not None:
        return result

    result = get_golang_crash_or_hang_location(output, src_path)
    if result is not None:
        return result

    if "<HANG_START>" not in output:
        return None

    re_minimal_hang_location = re.compile(
        r"^Line\s+(\d+)\s+of\s+\"?(.*)\"\s+starts", re.MULTILINE
    )  # groups: 1=line, 2=file
    re_hang_locatin_with_func = re.compile(
        r"^Line\s+(\d+)\s+of\s+\"?(.*?)\"?\s+starts.*?\<(.*?)(?:\>|\()",
        re.MULTILINE,
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
    result = get_dotnet_crash_or_hang_location(t, src_path)
    log.trace("dotnet location result: %s", result)
    if result is not None:
        return result

    result = get_golang_crash_or_hang_location(t, src_path)
    log.trace("golang location result: %s", result)
    if result is not None:
        return result

    result = get_gdb_crash_location(t, src_path)
    log.trace("gdb location result: %s", result)
    if result is not None:
        return result

    # no gdb output detected
    log.debug("no gdb stacktrace found")

    result = get_sanitizer_crash_location(t, src_path)
    log.trace("sanitizer location result: %s", result)
    if result is not None:
        return result

    log.debug("wasn't able to determine crash location")
    return None


def get_dotnet_crash_or_hang_location(
    output: Optional[str], src_path: Optional[str] = None
) -> Optional[str]:
    """
    Find first user code in .NET stack trace.
    If user code can't be found, return topmost location in stack trace.
    If it can't be found, return None
    """
    if not output:
        return None

    src_path = src_path or ""
    re_dotnet_stacktrace = re.compile(
        r"^\s+at\s+.*?\s+in\s+(.*?)\s*:\s*line\s+(\d+)\s*$", re.MULTILINE
    )
    # groups: 1=file, 2=line

    saved_match = re_dotnet_stacktrace.search(output)
    log.trace("first match: %s", saved_match)
    if not saved_match:
        return None

    for m in re_dotnet_stacktrace.finditer(output):
        log.trace("match in loop: %s", m)
        if m.group(1).startswith(src_path):
            saved_match = m
            break

    file_path = saved_match.group(1)
    file_line = saved_match.group(2)

    re_dotnet_issue_type = re.compile(
        r"^\s*Unhandled exception\W+\s+(.*?)\W\s", re.MULTILINE
    )
    m = re_dotnet_issue_type.search(output)
    log.trace("issue type match: %s", m)
    issue_type = (m.group(1) + " ") if m else ""

    location = f"{issue_type}at {file_path}:{file_line}"
    log.debug("dotnet location: %s", location)
    return location


def get_golang_crash_or_hang_location(
    output: Optional[str], src_path: Optional[str] = None
) -> Optional[str]:
    """
    Find first user code in golang stack trace.
    If user code can't be found, return first location in stack trace.
    If it can't be found, return None
    """
    if not output:
        return None

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


def get_gdb_crash_location(
    output: Optional[str], src_path: Optional[str] = None
) -> Optional[str]:
    """
    Extract crash location (source file, line, column) from given application output.
    output: application run output
    src_path: path to sources when the application was built; directory may not exist
    return None if crash location can not be extracted.
    """

    if not output:
        return None

    t = output

    re_check_gdb = re.compile(r".*^#\d+\s+0[xX].*?in", re.MULTILINE | re.DOTALL)

    if re.match(re_check_gdb, t) is None:
        return None

    re_gdb_location = re.compile(
        r"^#\d+\s+(?:0[xX][\S]{1,}\s+)?((?:in\s+)?.*\s+(?:at|from).*?$)", re.MULTILINE
    )
    locations = re.findall(re_gdb_location, t)

    if not locations:
        return None

    log.verbose3(
        "GDB STACKTRACE FOUND, location candidates:\n\t" + "\n\t".join(locations)
    )

    gdb_check_src_location = r"(?:in\s+)?(.*?)\s+at\s+("
    if src_path:
        gdb_check_src_location += src_path
    gdb_check_src_location += r".*?)$"
    log.debug("gdb_check_src_location: %s", gdb_check_src_location)
    re_gdb_check_src_location = re.compile(gdb_check_src_location)

    result = None
    # return first src location
    for location in locations:
        if re.match(re_gdb_check_src_location, location):
            result = location
            break

    # no src locations, return topmost location of the stack trace
    if result is None:
        result = locations[0]

    if not result[0:3] in ("in ", "at "):
        result = "in " + result

    return result


def get_sanitizer_crash_location(
    output: Optional[str], src_path: Optional[str]
) -> Optional[str]:
    """
    Return bug description for sanitizer errors (crashes), possibly including:
        issue_type
        file_path
        line_number
        column_number
    Examples of returned strings:
    ```
        stack-overflow in main at main.cpp:42:8
        in main at main.cpp:46:8
        at fuzz.cpp:12:11
    ```
    Return None if no such string can be extracted.
    """
    if not output:
        return None

    t = output
    log.trace("text to match (in square brackets): [%s]", t)

    # TODO: split this func by sanitizers

    # lsan
    re_leak_summary = re.compile(
        r"^\s*SUMMARY:\s+(\S+Sanitizer):\s+.*\sleaked\s+in\s+(\d+)\s+allocation.*\.\s*$",
        re.MULTILINE,
    )
    leak_summary = re.search(re_leak_summary, t)
    if leak_summary:
        # possible values: AddressSanitizer, LeakSanitizer?
        # sanitizer_name = leak_summary.group(1)

        # number of non-freed memory allocs
        num_allocs = int(leak_summary.group(2))

        if num_allocs >= 1:
            # parse stack trace and return topmost user code location
            # TODO: do something better with multiple allocations
            log.trace("src_path = %s", src_path)
            str_lsan_location = (
                r"^\s*#\S+\s+0[xX]\S+\s+(?:in)\s+([^\s\(]+)(?:\(.*?\))?\s*("
            )
            if src_path:
                str_lsan_location += src_path
            str_lsan_location += r".*?)\s*$"
            re_lsan_location = re.compile(str_lsan_location, re.MULTILINE)
            location = re.search(re_lsan_location, t)
            if location:
                func_name = location.group(1)
                src_location = location.group(2)
                return "in " + func_name + " at " + src_location

        # 0 alloc locations? location not matched by regex?
        # try to parse other sanitizers' messages

    # ubsan/cfisan
    re_ubsan_cfisan_location = re.compile(
        r"^\s*SUMMARY:\s+(\S+Sanitizer):\s+(\S+)\s+(.*?)\s+in\s*?$", re.MULTILINE
    )
    location = re.search(re_ubsan_cfisan_location, t)
    log.trace("ubsan/cfisan location1 = %s", location)
    if location:
        # 1 = sanitizer name (UndefinedBehaviorSanitizer)
        # 2 = issue type (undefined-behavior)
        # 3 = file, line, column (/src/src/fuzzable_app.cpp:29:31)
        return "at " + location.group(3)

    re_ubsan_cfisan_location2 = re.compile(
        r"^\s*(.*?:\d+:\d+):\s+runtime error:\s", re.MULTILINE
    )
    location = re.search(re_ubsan_cfisan_location2, t)
    log.trace("ubsan/cfisan location2 = %s", location)
    if location:
        # 1 = file, line, column
        return "at " + location.group(1)

    # asan
    re_asan_location = re.compile(
        r"^\s*SUMMARY:\s+AddressSanitizer:\s+(\S+)\s+(.*?)\s+in\s+(.*?)\s*$",
        re.MULTILINE,
    )
    location = re.search(re_asan_location, t)
    if location:
        # 1 = issue type (global-buffer-overflow)
        # 2 = file, line, column (/src/src/fuzzable_app.cpp:38:22)
        # 3 = function name (fuzz)
        issue_type = location.group(1)
        if issue_type == "SEGV":
            return "in " + location.group(3) + " at " + location.group(2)

        return issue_type + " in " + location.group(3) + " at " + location.group(2)

    return None


def location_to_file_line(
    location: Optional[str],
) -> Tuple[Optional[str], Optional[int]]:
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
