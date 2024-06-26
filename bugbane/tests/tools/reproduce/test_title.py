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

from typing import Optional
from bugbane.tools.reproduce.issue_card import IssueCard
from bugbane.tools.reproduce.trace_utils import get_crash_location, get_hang_location
from bugbane.tools.reproduce.verdict import Verdict

from bugbane.modules.log import get_verbose_logger

get_verbose_logger(__name__, 3)


def helper_make_card(
    output: Optional[str],
    exit_code: Optional[int],
    is_hang: Optional[bool],
    src_path: Optional[str] = None,
) -> IssueCard:
    card = IssueCard()
    card.output = output
    card.verdict = Verdict.from_run_results(
        exit_code=exit_code, is_hang=is_hang, output=card.output
    )
    card.load_location_and_set_title(src_path)
    return card


def test_asan_lsan_leak():
    output = """==18408==ERROR: LeakSanitizer: detected memory leaks

Direct leak of 123 byte(s) in 1 object(s) allocated from:
    #0 0x563af7d90f79 in malloc (/fuzz/libFuzzer/asan/fuzz/fuzzme+0x125f79)
    #1 0x563af7dd8173 in is_data_valid__leak /src/cpp/fuzz/../include/funcs.hpp:46:26
    #2 0x563af7dd8173 in ParseData(unsigned char const*, long) /src/cpp/fuzz/../include/funcs.hpp:89:13
    #3 0x563af7dd8400 in LLVMFuzzerTestOneInput /src/cpp/fuzz/fuzz.cpp:6:5
    #4 0x563af7cbacc8 in fuzzer::Fuzzer::ExecuteCallback(unsigned char const*, unsigned long) (/fuzz/libFuzzer/asan/fuzz/fuzzme+0x4fcc8)
    #5 0x563af7c9a7e3 in fuzzer::RunOneTest(fuzzer::Fuzzer*, char const*, unsigned long) (/fuzz/libFuzzer/asan/fuzz/fuzzme+0x2f7e3)
    #6 0x563af7ca1f6f in fuzzer::FuzzerDriver(int*, char***, int (*)(unsigned char const*, unsigned long)) (/fuzz/libFuzzer/asan/fuzz/fuzzme+0x36f6f)
    #7 0x563af7c91247 in main (/fuzz/libFuzzer/asan/fuzz/fuzzme+0x26247)
    #8 0x7fae0867e28f  (/usr/lib/libc.so.6+0x2928f) (BuildId: 60df1df31f02a7b23da83e8ef923359885b81492)

SUMMARY: AddressSanitizer: 123 byte(s) leaked in 1 allocation(s).
"""
    card = helper_make_card(output, exit_code=77, is_hang=False, src_path="/src")
    assert (
        card.title
        == "Memory leak in is_data_valid__leak at /src/cpp/include/funcs.hpp:46"
    )


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


def test_ubsan_no_summary():
    output = """/src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/my_entities.h:1540:22: runtime error: load of value 253, which is not a valid value for type 'bool'
    #0 0x558cc6888c85 in ML_Data::operator=(ML_Data&&) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/my_entities.h:1540
    #1 0x558cc6888c85 in ML_mylib::processMLGroup(ML_LibInterface*, int, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/dl_my.cpp:586
    #2 0x558cc6b506b8 in ML_mylib::readMLGroups(std::istream&, ML_LibInterface*) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/dl_my.cpp:210
    #3 0x558cc6b5111f in ML_mylib::in(std::istream&, ML_LibInterface*) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/dl_my.cpp:145
    #4 0x558cc688f5f6 in main /src/app/somethng/src/worker/test/src/lib/mylib/myconverter.cpp:34
    #5 0x7f24a3f7d564 in __libc_start_main (/build/fuzz/asan/artifacts/parsers/bin/../lib/libc.so.6+0x28564)
    #6 0x558cc6890d6d in _start (/build/fuzz/asan/artifacts/parsers/bin/mylibparser+0x5e2d6d)
"""
    card = helper_make_card(output, exit_code=1, is_hang=False, src_path="/src")
    assert (
        card.title
        == "Undefined behavior at /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/my_entities.h:1540"
    )


def test_ubsan_no_summary_gdb():
    """UBSAN message inside GDB"""

    output = """Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
[New Thread 0x12345678 ]
/src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/my_entities.h:1540:22: runtime error: load of value 253, which is not a valid value for type 'bool'
    #0 0x558cc6888c85 in ML_Data::operator=(ML_Data&&) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/my_entities.h:1540
    #1 0x558cc6888c85 in ML_mylib::processMLGroup(ML_LibInterface*, int, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/dl_my.cpp:586
    #2 0x558cc6b506b8 in ML_mylib::readMLGroups(std::istream&, ML_LibInterface*) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/dl_my.cpp:210
    #3 0x558cc6b5111f in ML_mylib::in(std::istream&, ML_LibInterface*) /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/dl_my.cpp:145
    #4 0x558cc688f5f6 in main /src/app/somethng/src/worker/test/src/lib/mylib/myconverter.cpp:34
    #5 0x7f24a3f7d564 in __libc_start_main (/build/fuzz/asan/artifacts/parsers/bin/../lib/libc.so.6+0x28564)
    #6 0x558cc6890d6d in _start (/build/fuzz/asan/artifacts/parsers/bin/mylibparser+0x5e2d6d)
"""
    card = helper_make_card(output, exit_code=1, is_hang=False, src_path="/src")
    assert (
        card.title
        == "Undefined behavior at /src/app/somethng/src/worker/test/extern/mylib-1.2.3/src/my_entities.h:1540"
    )


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
    assert card.title == "Crash in just_abort at /src/include/funcs.h:12"


def test_failed_assert():
    output = """test: test.c:4: main: Assertion `0' failed.
Aborted (core dumped)
"""
    card = helper_make_card(output=output, exit_code=134, is_hang=None, src_path="/src")
    assert card.title == "Crash"


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

    assert card.title == "Crash in failed_assert at /src/include/funcs.h:17"


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


def test_go_hang_no_stack_trace():
    output = """program hanged (timeout 10 seconds)

signal: killed
"""
    card = helper_make_card(output, exit_code=2, is_hang=None, src_path="/src/go")
    assert card.title == "Hang"


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


def test_go_out_of_memory():
    output = """fatal error: runtime: out of memory

runtime stack:
runtime.throw({0x7ac6ea?, 0x57b8c00000?})
        runtime/panic.go:992 +0x71
runtime.sysMap(0xc000400000, 0x7fffffffea60?, 0x7fffffffeac8?)
        runtime/mem_linux.go:189 +0x11b
runtime.systemstack()
        runtime/asm_amd64.s:469 +0x49

goroutine 1 [running]:
runtime.systemstack_switch()
        runtime/asm_amd64.s:436 fp=0xc0000e1500 sp=0xc0000e14f8 pc=0x461f60
reflect.unsafe_NewArray(0x4?, 0x4?)
        runtime/malloc.go:1296 +0x19 fp=0xc0000e1658 sp=0xc0000e1638 pc=0x45e579
reflect.MakeSlice({0x808870, 0x74a080}, 0xff303030, 0xff303030)
        /usr/local/go/src/reflect/value.go:2911 +0x17c fp=0xc0000e1688 sp=0xc0000e1658 pc=0x4cdd1c
construct/v1.Unpack({0x7fffcadfe000, 0x8, 0x8}, {0xc0000e1958, 0x1, 0x38?})
        /src/go/ctl.go:360 +0x26a fp=0xc0000e1928 sp=0xc0000e18e8 pc=0x7185aa
handler.(*Request).GetRequest(...)
        /src/go/request.go:33
go-fuzz-dep.Main({0xc0000e1f68, 0x1, 0x74c860?})
        go-fuzz-dep/main.go:36 +0x15a fp=0xc0000e1f50 sp=0xc0000e1ea8 pc=0x489fda
main.main()
        abc/def/command/go.fuzz.main/main.go:15 +0x3b fp=0xc0000e1f80 sp=0xc0000e1f50 pc=0x72de5b
runtime.main()
        runtime/proc.go:250 +0x212 fp=0xc0000e1fe0 sp=0xc0000e1f80 pc=0x437b72
runtime.goexit()
        runtime/asm_amd64.s:1571 +0x1 fp=0xc0000e1fe8 sp=0xc0000e1fe0 pc=0x464181
exit status 2
"""
    card = helper_make_card(output, exit_code=2, is_hang=None, src_path="/src/go")
    assert card.title == "Out of memory in v1.Unpack at /src/go/ctl.go:360"


def test_go_out_of_memory_no_stack_trace():
    output = """fatal error: runtime: out of memory
"""
    card = helper_make_card(output, exit_code=2, is_hang=None, src_path="/src/go")
    assert card.title == "Out of memory"


def test_csharp_unhandled_exception():
    """C# fuzz target tested with SharpFuzz."""

    output = """Unhandled exception. System.ArgumentOutOfRangeException: Specified argument was out of the range of valid values. (Parameter 'start')
   at System.Text.RegularExpressions.RegexInterpreter.FindFirstChar()
   at System.Text.RegularExpressions.RegexRunner.Scan(Regex regex, String text, Int32 textbeg, Int32 textend, Int32 textstart, Int32 prevlen, Boolean quick, TimeSpan timeout)
   at System.Text.RegularExpressions.Regex.Run(Boolean quick, Int32 prevlen, String input, Int32 beginning, Int32 length, Int32 startat)
   at System.Text.RegularExpressions.Regex.Match(String input)
   at Program.<>c__DisplayClass0_0.<<Main>$>b__0(String str) in /home/builder/fuzz/targets/System.Text.RegularExpressions/Program.cs:line 21
   at SharpFuzz.Fuzzer.<>c__DisplayClass11_0.<Wrap>b__0(Stream stream)
   at SharpFuzz.Fuzzer.RunWithoutAflFuzz(Action`1 action, Stream stream)
   at SharpFuzz.Fuzzer.Run(Action`1 action)
   at SharpFuzz.Fuzzer.Run(Action`1 action, Int32 bufferSize)
   at Program.<Main>$(String[] args) in /home/builder/fuzz/targets/System.Text.RegularExpressions/Program.cs:line 6
Aborted
"""
    card = helper_make_card(
        output, exit_code=134, is_hang=None, src_path="/home/builder/fuzz/targets"
    )
    assert (
        card.title
        == "Unhandled exception System.ArgumentOutOfRangeException at /home/builder/fuzz/targets/System.Text.RegularExpressions/Program.cs:21"
    )


def test_atheris_uncaught_exception() -> None:
    """Uncaught Python exception detected with Atheris."""

    output = """INFO: Using built-in libfuzzer
WARNING: Failed to find function "__sanitizer_acquire_crash_state".
WARNING: Failed to find function "__sanitizer_print_stack_trace".
WARNING: Failed to find function "__sanitizer_set_death_callback".
INFO: Running with entropic power schedule (0xFF, 100).
INFO: Seed: 554069088
./fuzz.py: Running 1 inputs 1 time(s) each.
Running: artifacts/crash-0125e21e3b4d87bcc61d854f63e235a46a48e8e8

 === Uncaught Python exception: ===
ValueError: minute must be in 0..59
Traceback (most recent call last):
  File "/pyxyz/./fuzz.py", line 23, in TestOneInput
    context = xyz.load(data)
  File "/pyxyz/src/xyz/__init__.py", line 73, in load
    return parser.load_one()
  File "/pyxyz/src/xyz/parser.py", line 88, in load_one
    return self.make(item)
  File "/pyxyz/src/xyz/parser.py", line 112, in make
    data = self.make_inner(item)
  File "/pyxyz/src/xyz/parser.py", line 151, in make_inner
    data = parse_data(self, item)
  File "/pyxyz/src/xyz/parser.py", line 391, in make_stats
    return datetime.datetime(year, month, day, hour, minute, second, fraction,
ValueError: minute must be in 0..59

==187528== ERROR: libFuzzer: fuzz target exited
SUMMARY: libFuzzer: fuzz target exited
"""
    card = helper_make_card(output, exit_code=77, is_hang=None, src_path="/pyxyz/src")
    assert (
        card.title
        == "Unhandled exception ValueError in make_stats at /pyxyz/src/xyz/parser.py:391"
    )


def test_python_exception_without_message() -> None:
    """Uncaught Python exception without exception message."""

    output = """Traceback (most recent call last):
  File "/src/./prog.py", line 27, in <module>
    sys.exit(main())
             ^^^^^^
  File "/src/./prog.py", line 20, in main
    print(m[int(sys.argv[1])]())
          ^^^^^^^^^^^^^^^^^^^^^
  File "/src/./prog.py", line 15, in <lambda>
    1: lambda: check_data("1"),
               ^^^^^^^^^^^^^^^
  File "/src/parse.py", line 20, in check_data
    raise SpecialError()
parse.SpecialError
"""
    card = helper_make_card(output, exit_code=1, is_hang=None, src_path="/src")
    assert (
        card.title
        == "Unhandled exception parse.SpecialError in check_data at /src/parse.py:20"
    )


def test_python_exception_from_stdin() -> None:
    """Uncaught Python exception (code ran from stdin)."""

    output = """Traceback (most recent call last):
  File "<stdin>", line 27, in <module>
  File "<stdin>", line 20, in main
IndexError: list index out of range
"""
    card = helper_make_card(output, exit_code=1, is_hang=None, src_path="/src")
    assert card.title == "Unhandled exception IndexError in main at <stdin>:20"


def test_python_exception_causes_another_exception() -> None:
    """
    Uncaught Python exception which causes another uncaught exception.
    Happens when we don't catch exception raised by `raise from`.
    """

    output = """Traceback (most recent call last):
  File "/src/./prog.py", line 20, in main
    print(m[int(sys.argv[1])]())
          ^^^^^^^^^^^^^^^^^^^^^
  File "/src/./prog.py", line 16, in <lambda>
    2: lambda: load_data(""),
               ^^^^^^^^^^^^^
  File "/src/./prog.py", line 9, in load_data
    raise RuntimeError("no data provided")
RuntimeError: no data provided

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/src/./prog.py", line 27, in <module>
    sys.exit(main())
             ^^^^^^
  File "/src/./prog.py", line 22, in main
    raise TypeError("bad type") from e
TypeError: bad type
"""

    card = helper_make_card(output, exit_code=1, is_hang=None, src_path="/src")
    assert card.title == "Unhandled exception TypeError in main at /src/prog.py:22"


def test_python_exception_during_another_exception() -> None:
    """
    Uncaught Python exception which causes another uncaught exception.
    Happens when we don't catch exception raised in an `except` block
    via `raise` (not `raise from`).
    """

    output = """Traceback (most recent call last):
  File "/src/parse.py", line 3, in parse_data
    return parse_caller(_inner_parse(data))
                        ^^^^^^^^^^^^^^^^^^
  File "/src/parse.py", line 12, in _inner_parse
    return int(data)
           ^^^^^^^^^
ValueError: invalid literal for int() with base 10: '-'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/src/./prog.py", line 27, in <module>
    sys.exit(main())
             ^^^^^^
  File "/src/./prog.py", line 20, in main
    print(m[int(sys.argv[1])]())
          ^^^^^^^^^^^^^^^^^^^^^
  File "/src/./prog.py", line 17, in <lambda>
    3: lambda: load_data("-"),
               ^^^^^^^^^^^^^^
  File "/src/./prog.py", line 11, in load_data
    return parse_data(data)
           ^^^^^^^^^^^^^^^^
  File "/src/parse.py", line 5, in parse_data
    print("bad data! %d" % (data,))
          ~~~~~~~~~~~~~~~^~~~~~~~~
TypeError: %d format: a real number is required, not str
"""

    card = helper_make_card(output, exit_code=1, is_hang=None, src_path="/src")
    assert (
        card.title == "Unhandled exception TypeError in parse_data at /src/parse.py:5"
    )


def test_python_exception_in_stdlib() -> None:
    """Uncaught Python exception which happened in standard library."""

    output = """Traceback (most recent call last):
  File "/src/./prog.py", line 28, in <module>
    sys.exit(main())
             ^^^^^^
  File "/src/./prog.py", line 21, in main
    print(m[int(sys.argv[1])]())
          ^^^^^^^^^^^^^^^^^^^^^
  File "/src/./prog.py", line 18, in <lambda>
    4: lambda: call_stdlib(),
               ^^^^^^^^^^^^^
  File "/src/parse.py", line 32, in call_stdlib
    Thread(target=_thread_func).run()
  File "/usr/lib64/python3.11/threading.py", line 975, in run
    self._target(*self._args, **self._kwargs)
  File "/src/parse.py", line 30, in _thread_func
    re.compile("[A-")
  File "/usr/lib64/python3.11/re/__init__.py", line 227, in compile
    return _compile(pattern, flags)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib64/python3.11/re/__init__.py", line 294, in _compile
    p = _compiler.compile(pattern, flags)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib64/python3.11/re/_compiler.py", line 743, in compile
    p = _parser.parse(p, flags)
        ^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib64/python3.11/re/_parser.py", line 982, in parse
    p = _parse_sub(source, state, flags & SRE_FLAG_VERBOSE, 0)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib64/python3.11/re/_parser.py", line 457, in _parse_sub
    itemsappend(_parse(source, state, verbose, nested + 1,
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib64/python3.11/re/_parser.py", line 588, in _parse
    raise source.error("unterminated character set",
re.error: unterminated character set at position 0
"""

    card = helper_make_card(output, exit_code=1, is_hang=None, src_path="/src")
    assert (
        card.title == "Unhandled exception re.error in _thread_func at /src/parse.py:30"
    )


def test_python_exception_in_lambda() -> None:
    """Uncaught Python exception which happened in a lambda function."""

    output = """Traceback (most recent call last):
  File "/src/./prog.py", line 29, in <module>
    sys.exit(main())
             ^^^^^^
  File "/src/./prog.py", line 22, in main
    print(m[int(sys.argv[1])]())
          ^^^^^^^^^^^^^^^^^^^^^
  File "/src/./prog.py", line 19, in <lambda>
    5: lambda: None.a,
               ^^^^^^
AttributeError: 'NoneType' object has no attribute 'a'
"""

    card = helper_make_card(output, exit_code=1, is_hang=None, src_path="/src")
    assert (
        card.title
        == "Unhandled exception AttributeError in <lambda> at /src/prog.py:19"
    )


def test_python_exception_in_eval() -> None:
    """Uncaught Python exception which happened in an eval call."""

    output = """Traceback (most recent call last):
  File "/src/./prog.py", line 30, in <module>
    sys.exit(main())
             ^^^^^^
  File "/src/./prog.py", line 23, in main
    print(m[int(sys.argv[1])]())
          ^^^^^^^^^^^^^^^^^^^^^
  File "/src/./prog.py", line 20, in <lambda>
    6: lambda: evaluator("None()"),
               ^^^^^^^^^^^^^^^^^^^
  File "/src/parse.py", line 35, in evaluator
    eval(cmd)
  File "<string>", line 1, in <module>
TypeError: 'NoneType' object is not callable
"""

    card = helper_make_card(output, exit_code=1, is_hang=None, src_path="/src")
    assert (
        card.title == "Unhandled exception TypeError in evaluator at /src/parse.py:35"
    )


def test_python_aborted() -> None:
    """
    Python caught signal like SIGABRT.
    This will probably be detected by non-Python trace parsers.
    """

    output = """QWidget: Must construct a QApplication before a QWidget
Aborted
"""

    card = helper_make_card(output, exit_code=134, is_hang=None, src_path="/src")
    assert card.title == "Crash"


def test_python_aborted_with_src_location() -> None:
    """
    Python caught signal like SIGABRT.
    Here triggered by pytest, but can happen in other situations as well.
    """

    output = """Thread 0x00007f9715c296c0 (most recent call first):
  File "/src/test_qt.py", line 8 in _thread_func
  File "/usr/lib64/python3.11/threading.py", line 975 in run
  File "/usr/lib64/python3.11/threading.py", line 1038 in _bootstrap_inner
  File "/usr/lib64/python3.11/threading.py", line 995 in _bootstrap

Current thread 0x00007f971a2d9500 (most recent call first):
  File "/src/test_qt.py", line 15 in test_test
  File "/usr/lib/python3.11/site-packages/_pytest/python.py", line 194 in pytest_pyfunc_call
  File "/usr/lib/python3.11/site-packages/pluggy/_callers.py", line 77 in _multicall
  File "/usr/lib/python3.11/site-packages/_pytest/config/__init__.py", line 192 in console_main
  File "/usr/bin/pytest-3.11", line 33 in <module>

Extension modules: PyQt6.QtCore, PyQt6.QtGui, PyQt6.QtWidgets (total: 3)
Aborted
"""

    card = helper_make_card(output, exit_code=134, is_hang=None, src_path="/src")
    assert card.title == "Crash in test_test at /src/test_qt.py:15"


def test_no_errors():
    output = """Bad input data entered!
Leaving...
"""
    card = helper_make_card(output, exit_code=2, is_hang=False, src_path="/src")
    assert card.title == "No error occurred"


def test_hang():
    card = helper_make_card(output=None, exit_code=None, is_hang=True, src_path="/src")
    assert card.title == "Hang"


def test_unknown():
    card = helper_make_card(output=None, exit_code=None, is_hang=None, src_path="/src")
    assert card.title == "Wasn't able to determine verdict"
