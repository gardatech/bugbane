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

"""
This module tests generating titles from various output strings
"""

from bugbane.tools.reproduce.trace_utils import (
    post_process_location,
    anonymize_run_string,
    get_hang_location,
    get_gdb_crash_location,
)

from bugbane.modules.log import get_verbose_logger

get_verbose_logger(__name__, 3)


def test_post_process_location():
    location = "/path/to/some/../file.cpp:20:56"
    assert post_process_location(location) == "/path/to/file.cpp:20"
    assert post_process_location("") == ""
    assert post_process_location(None) is None

    # only line number, no column, double dots
    assert post_process_location("../file.cpp:20") == "../file.cpp:20"

    # more double dots
    assert post_process_location("../../file.cpp:20") == "../../file.cpp:20"

    # single dots
    assert post_process_location("././file.cpp") == "file.cpp"

    # no dots, line numbers or columns
    assert post_process_location("file.cpp") == "file.cpp"


def test_anonymize_run_string():
    assert anonymize_run_string("") == ""
    assert anonymize_run_string(None) is None
    assert anonymize_run_string("func(arg1=1, arg2=2)") == "func "
    assert anonymize_run_string("RIP = 0x1234567") == "RIP = 0xADDRESS"


def test_gdb_get_hang_location():
    output = """Reading symbols from ./cfisan/fuzzable_app...
Starting program: /fuzz/cfisan/fuzzable_app < "/mnt/out/s6/hangs/id:000003,src:000000+000003,time:6921,op:splice,rep:4"
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".

Program received signal SIGINT, Interrupt.
0x000000000023d3c1 in fuzz (buf=<optimized out>, len=<optimized out>) at /src/src/fuzzable_app.cpp:66
66              for (unsigned short i = 0; i < n; i++)
<HANG_START>
68                  sum += i;
Line 68 of "/src/src/fuzzable_app.cpp" starts at address 0x23d30d <fuzz(char*, long)+557> and ends at 0x23d319 <fuzz(char*, long)+569>.
66              for (unsigned short i = 0; i < n; i++)
Line 66 of "/src/src/fuzzable_app.cpp" starts at address 0x23d20d <fuzz(char*, long)+301> and ends at 0x23d233 <fuzz(char*, long)+339>.
68                  sum += i;
Line 68 of "/src/src/fuzzable_app.cpp" starts at address 0x23d30d <fuzz(char*, long)+557> and ends at 0x23d319 <fuzz(char*, long)+569>.
66              for (unsigned short i = 0; i < n; i++)
Line 66 of "/src/src/fuzzable_app.cpp" starts at address 0x23d20d <fuzz(char*, long)+301> and ends at 0x23d233 <fuzz(char*, long)+339>.
68                  sum += i;
Line 68 of "/src/src/fuzzable_app.cpp" starts at address 0x23d30d <fuzz(char*, long)+557> and ends at 0x23d319 <fuzz(char*, long)+569>.
<HANG_END>
A debugging session is active.

        Inferior 1 [process 407] will be killed.

Quit anyway? (y or n) [answered Y; input not from terminal]
"""
    # card = helper_make_card(output, exit_code=None, is_hang=None)
    assert (
        get_hang_location(output, src_path="/src")
        == "in fuzz at /src/src/fuzzable_app.cpp:68"
    )
    # assert card.title == "Hang in fuzz at /src/src/fuzzable_app.cpp:68"


def test_gdb_get_hang_location_no_hang():
    output = """Reading symbols from echo...
(No debugging symbols found in echo)
(gdb) r hello
Starting program: /usr/bin/echo hello
hello
[Inferior 1 (process 4624) exited normally]
(gdb) info line
No line number information available.
(gdb) q
"""
    # card = helper_make_card(output, exit_code=None, is_hang=None)
    assert get_hang_location(output, src_path="/src") is None
    # assert card.title == "Hang"


def test_gdb_get_hang_location_bad_run():
    output = """python: No such file or directory.
Starting program:  -c "from time import sleep; sleep(7)"
No executable file specified.
Use the "file" or "exec-file" command.
<HANG_START>
The program is not being run.
No line number information available.
The program is not being run.
No line number information available.
The program is not being run.
No line number information available.
The program is not being run.
No line number information available.
The program is not being run.
No line number information available.
<HANG_END>
"""
    # card = helper_make_card(output, exit_code=None, is_hang=None)
    assert get_hang_location(output, src_path="/src") is None
    # assert card.title == "Hang"


def test_gdb_get_crash_location_no_line_info():
    output = """
Program received signal SIGSEGV, Segmentation fault.
0x000055555555513d in main ()
#0  0x000055555555513d in main ()
A debugging session is active.

        Inferior 1 [process 6491] will be killed.

Quit anyway? (y or n) [answered Y; input not from terminal]
"""
    # card = helper_make_card(output, exit_code=None, is_hang=None)
    assert get_gdb_crash_location(output, src_path="/src") is None
    # assert card.title == "Crash"


def test_gdb_get_crash_location_src_root_not_found():
    output = """
Program received signal SIGSEGV, Segmentation fault.
make_segfault () at /tmp/t/src/test.c:3
3           *(int*)0 = 1;
#0  make_segfault () at /tmp/t/src/test.c:3
#1  0x000055555555515c in main (argc=1, argv=0x7fffffffe2f8) at /tmp/t/src/test.c:7
A debugging session is active.

        Inferior 1 [process 7122] will be killed.

Quit anyway? (y or n) [answered Y; input not from terminal]
"""
    # card = helper_make_card(output, exit_code=None, is_hang=None)
    location = get_gdb_crash_location(output, src_path="/src")
    assert location is not None
    assert location.startswith("in make_segfault")
    assert location.endswith("at /tmp/t/src/test.c:3")
    # assert card.title == "Crash"
