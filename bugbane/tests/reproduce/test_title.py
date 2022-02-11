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

"""
This module tests generating titles from various output strings
"""

from typing import Optional
from bugbane.tools.reproduce.issue_card import IssueCard
from bugbane.tools.reproduce.trace_utils import get_crash_location, get_hang_location
from bugbane.tools.reproduce.verdict import Verdict

from bugbane.modules.log import get_first_logger

get_first_logger(__name__, 3)


def helper_make_card(
    output: str, exit_code: int, is_hang: bool, src_path: Optional[str] = None
) -> IssueCard:
    card = IssueCard()
    card.output = output
    card.verdict = Verdict.from_run_results(
        exit_code=exit_code, is_hang=is_hang, output=card.output
    )
    card.load_location_and_set_title(src_path)
    return card


def test_ubsan():
    output = """/src/src/fuzzable_app.cpp:29:31: runtime error: load of misaligned address 0x000000d54da5 for type 'unsigned long', which requires 8 byte alignment
0x000000d54da5: note: pointer points here
 55 cd cd cd cd cd cd  cd cd cd cd cd cd cd cd  cd cd cd cd cd 00 00 00  00 00 00 00 00 00 00 00  00
             ^ 
    #0 0x23d58b in fuzz(char*, long) /src/src/fuzzable_app.cpp:29:31
    #1 0x23d8b9 in main /src/src/fuzzable_app.cpp:76:9
    #2 0x7ffff6be7554 in __libc_start_main (/lib64/libc.so.6+0x22554)
    #3 0x217468 in _start (/fuzz/ubsan+0x217468)

SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /src/src/fuzzable_app.cpp:29:31 in 
"""

    card = helper_make_card(output, exit_code=1, is_hang=False)
    assert card.title == "Undefined behavior at /src/src/fuzzable_app.cpp:29"


def test_cfisan():
    output = """/src/src/fuzzable_app.cpp:47:17: runtime error: control flow integrity check for type 'int ()' failed during indirect function call
(/fuzz/cfisan+0xd545e5): note: _fini defined here
    #0 0x23d1bf in fuzz(char*, long) /src/src/fuzzable_app.cpp:47:17
    #1 0x23d375 in main /src/src/fuzzable_app.cpp:76:9
    #2 0x7ffff6be7554 in __libc_start_main (/lib64/libc.so.6+0x22554)
    #3 0x2172c8 in _start (/fuzz/cfisan+0x2172c8)

SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior /src/src/fuzzable_app.cpp:47:17 in 
"""

    card = helper_make_card(output, exit_code=1, is_hang=False)
    assert (
        card.title == "Control flow intergity violation at /src/src/fuzzable_app.cpp:47"
    )


def test_gdb_segv():
    output = """warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".

Program received signal SIGSEGV, Segmentation fault.
0x0000000000d54da5 in __afl_fuzz_alt ()
#0  0x0000000000d54da5 in __afl_fuzz_alt ()
#1  0x000000000023d3da in fuzz(char*, long) (buf=0xd54da0 <__afl_fuzz_alt> "F2\315\353!!\315\353\002A3434", len=<optimized out>) at /src/src/fuzzable_app.cpp:47
#2  0x000000000023d8ba in main (argc=1, argv=0x7fffffffebd8) at /src/src/fuzzable_app.cpp:76
A debugging session is active.

	Inferior 1 [process 346] will be killed.

Quit anyway? (y or n) [answered Y; input not from terminal]
"""
    # python gets exit code of gdb itself, which is 0
    card = helper_make_card(output, exit_code=0, is_hang=False)
    assert card.title == "Crash in fuzz at /src/src/fuzzable_app.cpp:47"


def test_gdb_abort():
    output = """warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".
Calling just_abort()

Program received signal SIGABRT, Aborted.
0x00007ffff6bfb387 in raise () from /lib64/libc.so.6
#0  0x00007ffff6bfb387 in raise () from /lib64/libc.so.6
#1  0x00007ffff6bfca78 in abort () from /lib64/libc.so.6
#2  0x000000000023d1d1 in just_abort() () at /src/src/../include/funcs.h:12
#3  0x000000000023d48b in fuzz(char*, long) (buf=0xd54da0 <__afl_fuzz_alt> "", len=<optimized out>) at /src/src/fuzzable_app.cpp:35
#4  0x000000000023d8ba in main (argc=1, argv=0x7fffffffebd8) at /src/src/fuzzable_app.cpp:76
A debugging session is active.

	Inferior 1 [process 334] will be killed.

Quit anyway? (y or n) [answered Y; input not from terminal]
"""
    # python gets exit code of gdb itself, which is 0
    card = helper_make_card(output, exit_code=0, is_hang=False)
    assert card.title == "Crash in just_abort at /src/src/../include/funcs.h:12"


def test_gdb_failed_assert():
    output = """warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".
ubsan: /src/src/../include/funcs.h:17: void failed_assert(): Assertion `false' failed.
Calling failed_assert()

Program received signal SIGABRT, Aborted.
0x00007ffff6bfb387 in raise () from /lib64/libc.so.6
#0  0x00007ffff6bfb387 in raise () from /lib64/libc.so.6
#1  0x00007ffff6bfca78 in abort () from /lib64/libc.so.6
#2  0x00007ffff6bf41a6 in __assert_fail_base () from /lib64/libc.so.6
#3  0x00007ffff6bf4252 in __assert_fail () from /lib64/libc.so.6
#4  0x000000000023d205 in failed_assert() () at /src/src/../include/funcs.h:17
#5  0x000000000023d4d7 in fuzz(char*, long) (buf=0xd54da0 <__afl_fuzz_alt> "1\243\006Z223\"", len=<optimized out>) at /src/src/fuzzable_app.cpp:40
#6  0x000000000023d8ba in main (argc=1, argv=0x7fffffffebd8) at /src/src/fuzzable_app.cpp:76
A debugging session is active.

	Inferior 1 [process 323] will be killed.

Quit anyway? (y or n) [answered Y; input not from terminal]
"""
    # python gets exit code of gdb itself, which is 0
    card = helper_make_card(output, exit_code=0, is_hang=False)

    assert card.title == "Crash in failed_assert at /src/src/../include/funcs.h:17"


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
    card = helper_make_card(output, exit_code=None, is_hang=None)
    assert (
        get_hang_location(output, src_path="/src")
        == "in fuzz at /src/src/fuzzable_app.cpp:68"
    )
    assert card.title == "Hang in fuzz at /src/src/fuzzable_app.cpp:68"


def test_location_is_in_user_code():
    output = """warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".
Calling process()

Program received signal SIGSEGV, Segmentation fault.
0x00007febd55631b0 in wcslen () from /lib64/libc.so.6
#0  0x00007febd55631b0 in wcslen () from /lib64/libc.so.6
#1  0x00007febd556472c in wcsrtombs () from /lib64/libc.so.6
#2  0x00007febd550825a in vfprintf () from /lib64/libc.so.6
#3  0x000000000026f1dd in __interceptor_printf () at /llvm-project/compiler-rt/lib/asan/../sanitizer_common/sanitizer_common_interceptors.inc:1643
#4  0x00000000003019bc in process (buf=0xe2ef00 <__afl_fuzz_alt> "F\270%S\020\020", len=8) at /src/src/fuzzable_app.cpp:12
#5  fuzz (buf=0xe2ef00 <__afl_fuzz_alt> "F\270%S\020\020", len=8) at /src/src/fuzzable_app.cpp:31
#6  0x0000000000302812 in main (argc=1, argv=0x7ffc13207e08) at /src/src/fuzzable_app.cpp:98
A debugging session is active.

        Inferior 1 [process 45] will be killed.

Quit anyway? (y or n) [answered Y; input not from terminal]
"""
    card = helper_make_card(output, exit_code=0, is_hang=False, src_path="/src")
    assert card.title == "Crash in process at /src/src/fuzzable_app.cpp:12"


def test_go_index_out_of_range():
    output = """panic: runtime error: index out of range [38] with length 4

goroutine 1 [running]:
_/src/go.check_index({0x7f3bb92cc000, 0x4, 0x0}, 0x0)
        /src/go/fuzzable.go:8 +0xf0
_/src/go.Parse({0x7f3bb92cc000, 0xc000108e98, 0x4})
        /src/go/fuzzable.go:64 +0x165
_/src/go.Fuzz({0x7f3bb92cc000, 0xc000036730, 0x40b894})
        /src/go/fuzz.go:6 +0x37
go-fuzz-dep.Main({0xc000108f68, 0x1, 0x4983c0})
        go-fuzz-dep/main.go:36 +0x15b
main.main()
        _/src/go/go.fuzz.main/main.go:15 +0x3b
exit status 2"""

    card = helper_make_card(output, exit_code=2, is_hang=None, src_path="/src")
    assert card.title == "Panic in go.check_index at /src/go/fuzzable.go:8"


def test_go_stack_overflow():
    output = """runtime: goroutine stack exceeds 1000000000-byte limit
runtime: sp=0xc0200e0390 stack=[0xc0200e0000, 0xc0400e0000]
fatal error: stack overflow

runtime stack:
runtime.throw({0x468ab8, 0x4c59a0})
        runtime/panic.go:1198 +0x71
runtime.newstack()
        runtime/stack.go:1088 +0x5ac
runtime.morestack()
        runtime/asm_amd64.s:461 +0x8b

goroutine 1 [running]:
_/src/go.recursive_sum({0x7f31cb7c2000, 0x3, 0x3}, 0x92490c)
        /src/go/fuzzable.go:3 +0x179 fp=0xc0200e03a0 sp=0xc0200e0398 pc=0x459dd9
_/src/go.recursive_sum({0x7f31cb7c2000, 0x0, 0x0}, 0x0)
        /src/go/fuzzable.go:13 +0x13d fp=0xc0200e03d8 sp=0xc0200e03a0 pc=0x459d9d
_/src/go.recursive_sum({0x7f31cb7c2000, 0x0, 0x0}, 0x0)
        /src/go/fuzzable.go:13 +0x13d fp=0xc0200e0410 sp=0xc0200e03d8 pc=0x459d9d
_/src/go.recursive_sum({0x7f31cb7c2000, 0x0, 0x0}, 0x0)
        /src/go/fuzzable.go:13 +0x13d fp=0xc0200e0448 sp=0xc0200e0410 pc=0x459d9d
_/src/go.recursive_sum({0x7f31cb7c2000, 0x0, 0x0}, 0x0)
        /src/go/fuzzable.go:13 +0x13d fp=0xc0200e1948 sp=0xc0200e1910 pc=0x459d9d
...additional frames elided..."""

    card = helper_make_card(output, exit_code=2, is_hang=None, src_path="/src")
    assert card.title == "Stack overflow in go.recursive_sum at /src/go/fuzzable.go:3"


def test_go_hang():
    output = """program hanged (timeout 10 seconds)

SIGABRT: abort
PC=0x456420 m=0 sigcode=0

goroutine 0 [idle]:
runtime.epollwait()
        runtime/sys_linux_amd64.s:666 +0x20
runtime.netpoll(0xc00001c000)
        runtime/netpoll_epoll.go:127 +0xdc
runtime.findrunnable()
        runtime/proc.go:2947 +0x593
runtime.schedule()
        runtime/proc.go:3367 +0x239
runtime.park_m(0xc0000001a0)
        runtime/proc.go:3516 +0x14d
runtime.mcall()
        runtime/asm_amd64.s:307 +0x43

goroutine 1 [sleep]:
time.Sleep(0x2540be400)
        runtime/time.go:193 +0x12e
_/src/go.Parse({0x7f94c0cc9000, 0xc00009ae98, 0x459317})
        /src/go/fuzzable.go:48 +0x9e
_/src/go.Fuzz({0x7f94c0cc9000, 0xc000036730, 0x40ad54})
        /src/go/fuzz.go:6 +0x37
go-fuzz-dep.Main({0xc00009af68, 0x1, 0x45f060})
        go-fuzz-dep/main.go:36 +0x15b
main.main()
        _/src/go/go.fuzz.main/main.go:15 +0x3b

rax    0xfffffffffffffffc
rbx    0x1
rcx    0x456420
rdx    0x80
rdi    0x6
rsi    0x7ffd48eba1e8
rbp    0x7ffd48eba7e8
rsp    0x7ffd48eba190
r8     0x0
r9     0x21160468890
r10    0x270f
r11    0x246
r12    0x7ffd48eba218
r13    0x1
r14    0x4c96e0
r15    0xffffffffffffffff
rip    0x456420
rflags 0x246
cs     0x33
fs     0x0
gs     0x0
exit status 2"""

    card = helper_make_card(output, exit_code=2, is_hang=None, src_path="/src/go")
    assert card.title == "Hang in go.Parse at /src/go/fuzzable.go:48"


def test_go_segfault():
    output = """panic: runtime error: invalid memory address or nil pointer dereference
[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x459c81]

goroutine 1 [running]:
_/src/go.Parse(...)
        /src/go/fuzzable.go:9
_/src/go.Fuzz({0x7efc08132000, 0x0, 0x40ac74})
        /src/go/fuzz.go:6 +0xa1
go-fuzz-dep.Main({0xc000068f68, 0x1, 0x45e060})
        go-fuzz-dep/main.go:36 +0x15b
main.main()
        _/src/go/go.fuzz.main/main.go:15 +0x3b
exit status 2"""
    card = helper_make_card(output, exit_code=2, is_hang=None, src_path="/src")
    assert card.title == "Crash in go.Parse at /src/go/fuzzable.go:9"
