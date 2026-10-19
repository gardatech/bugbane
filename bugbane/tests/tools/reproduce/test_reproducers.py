# Copyright 2022-2026 Garda Technologies, LLC. All rights reserved.
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

from typing import List, Dict, Tuple, Optional, Type

import pytest
from pytest_mock import MockerFixture

from bugbane.tools.reproduce.reproducers.factory import ReproducerFactory
from bugbane.tools.reproduce.reproducers.reproducer import Reproducer
from bugbane.tools.reproduce.reproducers.default_reproducer import (
    DefaultReproducer,
    output_has_gdb_traceback,
)
from bugbane.tools.reproduce.issue_card import IssueCard
from bugbane.tools.reproduce.verdict import Verdict
from bugbane.tools.reproduce.reproducers.gofuzz import GoFuzzReproducer
from bugbane.tools.reproduce.reproducers.gotest import GoTestReproducer


@pytest.mark.parametrize(
    "fuzzer_type, reproducer_class",
    [
        ("AFL++", DefaultReproducer),
        ("libFuzzer", DefaultReproducer),
        ("go-fuzz", GoFuzzReproducer),
        ("go-test", GoTestReproducer),
    ],
)
def test_factory_by_fuzzer_type(fuzzer_type: str, reproducer_class: Type[Reproducer]):
    assert ReproducerFactory.create(fuzzer_type).__class__ is reproducer_class


@pytest.mark.parametrize(
    "reproduce_cmd, reproducer_class",
    [
        (
            'ubsan/app "./out/target/crashes/id:000000,sig:06,sync:m1,src:000000"',
            DefaultReproducer,
        ),
        (
            './app --file "./out/target/hangs/id:000000,sig:06,sync:m1,src:000000"',
            DefaultReproducer,
        ),
        ('myapp "./artifacts/crash-1234567890"', DefaultReproducer),
        (
            """timeout --kill-after 9s -s SIGINT 2s gdb --ex 'r "artifacts/crash-57700c512968964cfaaea5932b3747cd99884f80"' --ex "q" ./asan/app 0</dev/null""",
            DefaultReproducer,
        ),
        (
            'cat "crashers/crash-57700c512968964cfaaea5932b3747cd99884f80"',
            GoFuzzReproducer,
        ),
        (
            "go test -run=FuzzMyFunc/57700c512968964cfaaea5932b3747cd99884f80",
            GoTestReproducer,
        ),
        (
            "go test -test.run=FuzzMyFunc/57700c512968964cfaaea5932b3747cd99884f80",
            GoTestReproducer,
        ),
    ],
)
def test_factory_by_reproduce_cmd(
    reproduce_cmd: str, reproducer_class: Type[Reproducer]
):
    assert (
        ReproducerFactory.create_from_reproduce_cmd(reproduce_cmd).__class__
        is reproducer_class
    )


def test_factory_bad(mocker: MockerFixture):
    mocker.patch.dict(ReproducerFactory.registry, {}, clear=True)
    mocker.patch.object(ReproducerFactory, "default", None)
    with pytest.raises(TypeError):
        ReproducerFactory.create("!! unknown !!")


def test_factory_overwrite():
    class ReproducerFactoryChild(ReproducerFactory):
        registry: Dict[str, Type[Reproducer]] = {}
        default: Optional[Type[Reproducer]] = None

    @ReproducerFactoryChild.register_default()
    class SomeClass1:
        pass

    assert len(ReproducerFactoryChild.registry) == 0
    assert ReproducerFactoryChild.default is SomeClass1

    @ReproducerFactoryChild.register_default()
    class SomeClass2:
        pass

    assert len(ReproducerFactoryChild.registry) == 0
    assert ReproducerFactoryChild.default is SomeClass2


@pytest.mark.parametrize(
    "samples_path, expected_run_args",
    [
        (
            "testdata/fuzz/FuzzParse/beefbeefbeef",
            "-test.run=FuzzParse/beefbeefbeef",
        ),
        (
            "/fuzz/myapp/testdata/fuzz/FuzzSimpleParse/beefbeefbeef",
            "-test.run=FuzzSimpleParse/beefbeefbeef",
        ),
    ],
)
def test_gotest_make_reproduce_cmd(samples_path: str, expected_run_args: str):
    r = GoTestReproducer()
    print(f"samples_path={samples_path}, expected_run_args={expected_run_args}")
    assert r.prep_run_args(sample_path=samples_path) == expected_run_args


@pytest.mark.parametrize(
    "reproducer, expected_ability_to_reproduce",
    [
        (DefaultReproducer, True),
        (GoFuzzReproducer, False),
        (GoTestReproducer, True),
    ],
)
def test_ability_to_run_tested_app(
    reproducer: Reproducer, expected_ability_to_reproduce: bool
) -> None:
    assert reproducer.can_run_tested_app() is expected_ability_to_reproduce


# gdb traceback test data as separate variables
# this is to avoid indexing into array by arbitrary numbers later on

output_1_tb = """warning: Error disabling address space randomization: Operation not permitted
Traceback (most recent call last):
  File "/usr/share/gdb/auto-load/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.30-gdb.py", line 61, in <module>
    register_libstdcxx_printers(gdb.current_objfile())
  File "/lib/x86_64-linux-gnu/../../share/gcc/python/libstdcxx/v6/__init__.py", line 31, in register_libstdcxx_printers
    if gdb_has_xmethods():
  File "/lib/x86_64-linux-gnu/../../share/gcc/python/libstdcxx/v6/__init__.py", line 21, in gdb_has_xmethods
    import gdb.xmethod
  File "/usr/share/gdb/python/gdb/xmethod.py", line 30, in <module>
    class XMethod(object):
KeyboardInterrupt
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
[New Thread 0x7ffff7443640 (LWP 400659)]
Killed
"""

output_1_clean = """warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
[New Thread 0x7ffff7443640 (LWP 400659)]
Killed
"""

output_2_tb = """Traceback (most recent call last):
  File "/usr/share/gdb/python/gdb/__init__.py", line 182, in _auto_load_packages
    __import__(modname)
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 879, in exec_module
  File "<frozen importlib._bootstrap_external>", line 1016, in get_code
  File "<frozen importlib._bootstrap_external>", line 1074, in get_data
KeyboardInterrupt

Reading symbols from ./basic/targets/myapp...
Starting program: /fuzz/basic/targets/myapp < "./out/myapp2/hangs/id:000005,src:000086+000116,time:718814,execs:23232,op:splice,rep:5"
warning: Error disabling address space randomization: Operation not permitted
Killed
"""

output_2_clean = """Reading symbols from ./basic/targets/myapp...
Starting program: /fuzz/basic/targets/myapp < "./out/myapp2/hangs/id:000005,src:000086+000116,time:718814,execs:23232,op:splice,rep:5"
warning: Error disabling address space randomization: Operation not permitted
Killed
"""

output_3_tb = """Traceback (most recent call last):
  File "/usr/share/gdb/python/gdb/__init__.py", line 169, in _auto_load_packages
    __import__(modname)
  File "/usr/share/gdb/python/gdb/command/backtrace.py", line 21, in <module>
    from gdb.FrameIterator import FrameIterator
  File "<frozen importlib._bootstrap>", line 1007, in _find_and_load
  File "<frozen importlib._bootstrap>", line 986, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 680, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 846, in exec_module
  File "<frozen importlib._bootstrap_external>", line 958, in get_code
  File "<frozen importlib._bootstrap_external>", line 1040, in get_data
KeyboardInterrupt

Reading symbols from fuzz/basic/myapp...
Starting program: /path/to/fuzz/basic/myapp - < "fuzz/out/myapp01/hangs/id:000000,sync:myapp05,src:000035"
warning: Error disabling address space randomization: Operation not permitted
Missing separate debuginfo for /lib64/ld-linux-x86-64.so.2
Try to install the hash file /usr/lib/debug/.build-id/c4/4c77f9a2c1c59068378067d8101b47857aec4f.debug
Missing separate debuginfo for /lib64/libdl.so.2
Try to install the hash file /usr/lib/debug/.build-id/89/ca9147bed133663c1965eada6d4f52de05bd23.debug
Missing separate debuginfo for /lib64/libpthread.so.0
Try to install the hash file /usr/lib/debug/.build-id/d6/5b87273b47f6c2b46b41e293f74a0a7cad08ac.debug
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".
Missing separate debuginfo for /lib64/libstdc++.so.6
Try to install the hash file /usr/lib/debug/.build-id/90/b756b26040d4c6b9fed5302a9f6a95a91a8c78.debug
Missing separate debuginfo for /lib64/libm.so.6
Try to install the hash file /usr/lib/debug/.build-id/64/3b53e0b51ac3c66b9c40f4eb09cf368537b2ee.debug
Missing separate debuginfo for /lib64/libgcc_s.so.1
Try to install the hash file /usr/lib/debug/.build-id/ca/cf42385f6eab5190db54fedece9da06ea1a8c6.debug
Missing separate debuginfo for /lib64/libc.so.6
Try to install the hash file /usr/lib/debug/.build-id/e2/298e63d0cbddf0c17fc000c46ea87d15a910d7.debug
Reading 33344 bytes from -
Execution successful.
[Inferior 1 (process 2256994) exited normally]
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

output_3_clean = """Reading symbols from fuzz/basic/myapp...
Starting program: /path/to/fuzz/basic/myapp - < "fuzz/out/myapp01/hangs/id:000000,sync:myapp05,src:000035"
warning: Error disabling address space randomization: Operation not permitted
Missing separate debuginfo for /lib64/ld-linux-x86-64.so.2
Try to install the hash file /usr/lib/debug/.build-id/c4/4c77f9a2c1c59068378067d8101b47857aec4f.debug
Missing separate debuginfo for /lib64/libdl.so.2
Try to install the hash file /usr/lib/debug/.build-id/89/ca9147bed133663c1965eada6d4f52de05bd23.debug
Missing separate debuginfo for /lib64/libpthread.so.0
Try to install the hash file /usr/lib/debug/.build-id/d6/5b87273b47f6c2b46b41e293f74a0a7cad08ac.debug
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib64/libthread_db.so.1".
Missing separate debuginfo for /lib64/libstdc++.so.6
Try to install the hash file /usr/lib/debug/.build-id/90/b756b26040d4c6b9fed5302a9f6a95a91a8c78.debug
Missing separate debuginfo for /lib64/libm.so.6
Try to install the hash file /usr/lib/debug/.build-id/64/3b53e0b51ac3c66b9c40f4eb09cf368537b2ee.debug
Missing separate debuginfo for /lib64/libgcc_s.so.1
Try to install the hash file /usr/lib/debug/.build-id/ca/cf42385f6eab5190db54fedece9da06ea1a8c6.debug
Missing separate debuginfo for /lib64/libc.so.6
Try to install the hash file /usr/lib/debug/.build-id/e2/298e63d0cbddf0c17fc000c46ea87d15a910d7.debug
Reading 33344 bytes from -
Execution successful.
[Inferior 1 (process 2256994) exited normally]
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

output_4_tb = """Reading symbols from ./basic/targets/myapp...
Starting program: /fuzz/basic/targets/myapp < "./out/myapp2/hangs/id:000004,src:000191+000114,time:1328146,execs:43393,op:splice,rep:2"
warning: Error disabling address space randomization: Operation not permitted
Traceback (most recent call last):
  File "/usr/share/gdb/auto-load/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.30-gdb.py", line 61, in <module>
    register_libstdcxx_printers(gdb.current_objfile())
  File "/lib/x86_64-linux-gnu/../../share/gcc/python/libstdcxx/v6/__init__.py", line 28, in register_libstdcxx_printers
    from .printers import register_libstdcxx_printers
  File "/lib/x86_64-linux-gnu/../../share/gcc/python/libstdcxx/v6/printers.py", line 2351, in <module>
    build_libstdcxx_dictionary ()
  File "/lib/x86_64-linux-gnu/../../share/gcc/python/libstdcxx/v6/printers.py", line 2189, in build_libstdcxx_dictionary
    libstdcxx_printer = Printer("libstdc++-v6")
  File "/lib/x86_64-linux-gnu/../../share/gcc/python/libstdcxx/v6/printers.py", line 1795, in __init__
    self.compiled_rx = re.compile('^([a-zA-Z0-9_:]+)(<.*>)?$')
  File "/usr/lib/python3.10/re.py", line 251, in compile
    return _compile(pattern, flags)
  File "/usr/lib/python3.10/re.py", line 303, in _compile
    p = sre_compile.compile(pattern, flags)
  File "/usr/lib/python3.10/sre_compile.py", line 788, in compile
    p = sre_parse.parse(p, flags)
  File "/usr/lib/python3.10/sre_parse.py", line 955, in parse
    p = _parse_sub(source, state, flags & SRE_FLAG_VERBOSE, 0)
  File "/usr/lib/python3.10/sre_parse.py", line 444, in _parse_sub
    itemsappend(_parse(source, state, verbose, nested + 1,
  File "/usr/lib/python3.10/sre_parse.py", line 846, in _parse
    state.closegroup(group, p)
  File "/usr/lib/python3.10/sre_parse.py", line 98, in closegroup
    self.groupwidths[gid] = p.getwidth()
  File "/usr/lib/python3.10/sre_parse.py", line 221, in getwidth
    self.width = min(lo, MAXREPEAT - 1), min(hi, MAXREPEAT)
KeyboardInterrupt
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
[New Thread 0x7ffff7443640 (LWP 399949)]
?[38;2;255;000;000m[2026-12-31T23:59:59] myapp (399946) Error: mylib/myapp.cpp:716: ?[0m?[38;2;255;000;000mUnknown byte: 37?[0m
?[38;2;255;000;000m[2026-12-31T23:59:59] myapp (399946) Error: mylib/myapp.cpp:716: ?[0m?[38;2;255;000;000mUnknown byte: ffffffe9?[0m
Killed
"""

output_4_clean = """Reading symbols from ./basic/targets/myapp...
Starting program: /fuzz/basic/targets/myapp < "./out/myapp2/hangs/id:000004,src:000191+000114,time:1328146,execs:43393,op:splice,rep:2"
warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
[New Thread 0x7ffff7443640 (LWP 399949)]
?[38;2;255;000;000m[2026-12-31T23:59:59] myapp (399946) Error: mylib/myapp.cpp:716: ?[0m?[38;2;255;000;000mUnknown byte: 37?[0m
?[38;2;255;000;000m[2026-12-31T23:59:59] myapp (399946) Error: mylib/myapp.cpp:716: ?[0m?[38;2;255;000;000mUnknown byte: ffffffe9?[0m
Killed
"""

output_5_tb = """Traceback (most recent call last):
  File "/usr/share/gdb/python/gdb/__init__.py", line 144, in auto_load_packages
    __import__(modname)
  File "<frozen importlib._bootstrap>", line 983, in _find_and_load
  File "<frozen importlib._bootstrap>", line 967, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 677, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 724, in exec_module
  File "<frozen importlib._bootstrap_external>", line 859, in get_code
  File "<frozen importlib._bootstrap_external>", line 917, in get_data
KeyboardInterrupt

Reading symbols from ./basic/myapp...Killed
"""

output_5_clean = """Reading symbols from ./basic/myapp...Killed
"""

# array of pairs for use with pytest.parametrize
gdb_traceback_output_pairs = [
    (output_1_tb, output_1_clean),
    (output_2_tb, output_2_clean),
    (output_3_tb, output_3_clean),
    (output_4_tb, output_4_clean),
    (output_5_tb, output_5_clean),
]


@pytest.mark.parametrize("traceback_output, clean_output", gdb_traceback_output_pairs)
def test_output_has_gdb_traceback(traceback_output: str, clean_output: str) -> None:
    assert output_has_gdb_traceback(traceback_output) is True
    assert output_has_gdb_traceback(clean_output) is False


@pytest.mark.parametrize(
    "confirm_tries, cleanup_tries, run_outcomes, expected_card_count, expected_has_traceback",
    [
        # fmt: off

        # (confirm_arg, cleanup_arg, [(is_hang, has_tb), ...], num_issue_cards_returned, has_traceback)

        # confirm=0 & no cleanup -> only one app run
        (0, 0, [(True, True)], 1, True),  # traceback kept
        (0, 0, [(False, False)], 0, False),  # not a hang -> discarded

        # confirm=0, cleanup=1
        (0, 1, [(True, True), (True, False)], 1, False),  # traceback disappeared
        (0, 1, [(True, False)], 1, False),  # no traceback -> confirmed as is
        (0, 1, [(False, False)], 0, False),  # not a hang -> discarded
        (0, 1, [(True, True), (False, False)], 0, False),  # cleanup-reserved run didn't produce a hang -> discard

        # confirm=0, cleanup=2: cleanup tries didn't help
        (0, 2, [(True, True), (True, True), (True, True)], 1, True),  # keep traceback as is
        (0, 2, [(True, True), (True, True), (False, False)], 0, False),  # not a hang -> discard

        # cleanup disabled -> return as is, if hang present
        (1, 0, [(True, False), (True, False)], 1, False),  # 2 runs to confirm
        (1, 0, [(True, False), (False, False)], 0, False),  # 2nd run not a hang -> discard

        # confirm=1, cleanup=1: ok cleanup
        (1, 1, [(True, True), (True, False), (True, False)], 1, False),
        # confirm=1, cleanup=1: cleanup tries didn't help
        (1, 1, [(True, True), (True, True), (True, True)], 1, True),
        (1, 1, [(True, True), (False, False)], 0, False),  # cleanup-reserved run didn't produce a hang -> discard

        # confirm=2, cleanup=0: just 3 runs to confirm
        (2, 0, [(True, False), (True, False), (True, False)], 1, False),

        # confirm=2, cleanup=2: 5 runs (3 to confirm hang and 2 for cleanup)
        (2, 2, [(True, True), (True, True), (True, True), (True, True), (True, True)] , 1, True),
        # fmt: on
    ],
)
def test_run_binary_on_hangs(
    confirm_tries: int,
    cleanup_tries: int,
    run_outcomes: List[Tuple[bool, bool]],
    expected_card_count: int,
    expected_has_traceback: bool,
    mocker: MockerFixture,
) -> None:
    reproducer = DefaultReproducer()

    tb_output = output_3_tb
    clean_hang_output = output_3_clean
    non_hang_output = output_1_clean

    cards: List[IssueCard] = []
    for is_hang, has_tb in run_outcomes:
        if is_hang:
            output = tb_output if has_tb else clean_hang_output
            verdict = Verdict.HANG
        else:
            output = non_hang_output
            verdict = Verdict.NO_ERROR

        cards.append(
            IssueCard(
                verdict=verdict,
                output=output,
            )
        )

    mocker.patch.object(reproducer, "run", side_effect=cards)
    result: List[IssueCard] = reproducer.run_binary_on_hangs(  # pyright: ignore
        binary_path="/usr/bin/app",
        samples=["/path/to/sample"],
        hang_reproduce_limit=10,
        hang_confirm_tries=confirm_tries,
        hang_gdb_cleanup_tries=cleanup_tries,
    )

    assert len(result) == expected_card_count

    if expected_card_count == 1:
        assert output_has_gdb_traceback(result[0].output) is expected_has_traceback
