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

from typing import List, Dict

import pytest
from pytest_mock import MockerFixture

from bugbane.modules.build_type import BuildType
from bugbane.modules.string_utils import replace_part_in_str_list
from bugbane.tools.fuzz.command_utils import make_tmux_commands
from bugbane.modules.fuzzer_cmd.factory import FuzzerCmdFactory
from bugbane.modules.fuzzer_cmd.fuzzer_cmd import FuzzerCmd, FuzzerCmdError
from bugbane.modules.fuzzer_cmd.aflplusplus import AFLplusplusCmd
from bugbane.modules.fuzzer_cmd.libfuzzer import LibFuzzerCmd
from bugbane.modules.fuzzer_cmd.gofuzz import GoFuzzCmd
from bugbane.modules.fuzzer_cmd.gotest import GoTestCmd


def test_generate_commands():
    cmdgen = AFLplusplusCmd()

    cmd = cmdgen.generate_one("in", "out", run_env={})
    assert cmd == "afl-fuzz -i in -o out -m none -S $name -- $appname $run_args"

    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.LAF: "./laf/app",
        BuildType.CMPLOG: "./cmplog/app",
        BuildType.ASAN: "./asan/app",
        BuildType.UBSAN: "./ubsan/app",
        BuildType.CFISAN: "./cfisan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=17,
        builds=builds,
    )
    assert len(cmds) == 17


def test_replace_part_in_commands():
    count = 8
    base_cmd = (
        "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S $name -- $appname $run_args"
    )
    cmds = [base_cmd] * count

    # should not replace anything
    replace_part_in_str_list(cmds, "<<!!!notfound!!!>>", "12345", 1, len(cmds) - 1)
    assert all((cmd == base_cmd for cmd in cmds))

    # should replace only first cmd
    replace_part_in_str_list(cmds, " -S $name ", " -M $name ", 1, 0)
    assert " -M $name " in cmds[0]
    for i in range(1, count):
        assert " -M $name " not in cmds[i]

    # should replace only first cmd (end index provided)
    replace_part_in_str_list(cmds, " -M $name ", " -M $name -D ", 1, 0, len(cmds) - 1)
    assert " -M $name -D " in cmds[0]
    for i in range(1, count):
        assert " -M $name -D " not in cmds[i]

    # should replace all cmds
    replace_part_in_str_list(cmds, " $name ", " $name -p fast ", 1, 0, len(cmds) - 1)
    assert all((" -p fast " in cmd for cmd in cmds))


def test_replace_part_in_one_command():
    count = 1
    cmds = [
        "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S $name -- $appname $run_args"
    ] * count

    replace_part_in_str_list(cmds, " $name ", " $name -p fast ", 1, 0, len(cmds) - 1)
    assert all((" -p fast " in cmd for cmd in cmds))


def test_replace_cmds_index_basic():
    count = 2
    cmds = [
        "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S $name -- $appname $run_args"
    ] * count

    replace_part_in_str_list(cmds, " $name ", " fuzz0$i ", 1, 0, len(cmds) - 1)

    assert (
        cmds[0]
        == "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S fuzz01 -- $appname $run_args"
    )
    assert (
        cmds[1]
        == "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S fuzz02 -- $appname $run_args"
    )


def test_replace_cmds_index_zfill():
    count = 10
    cmds = [
        "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S $name -- $appname $run_args"
    ] * count

    replace_part_in_str_list(cmds, " $name ", " fuzz$i ", 1, 0, len(cmds) - 1)

    assert (
        cmds[0]
        == "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S fuzz01 -- $appname $run_args"
    )
    assert (
        cmds[-1]
        == "afl-fuzz -i /fuzz/in -o /fuzz/out -m none -S fuzz10 -- $appname $run_args"
    )


def test_aflpp_generate_cmds():
    cmdgen = AFLplusplusCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.LAF: "./laf/app",
        BuildType.CMPLOG: "./cmplog/app",
        BuildType.ASAN: "./asan/app",
        BuildType.UBSAN: "./ubsan/app",
        BuildType.CFISAN: "./cfisan/app",
        BuildType.COVERAGE: "./coverage/app",
    }
    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
    )
    print(cmds)
    helper_check_cmds(cmds, builds)


def test_aflpp_generate_specs():
    cmdgen = AFLplusplusCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }
    _, specs = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=4,
        builds=builds,
    )
    print(specs)
    assert "AFL++" in specs
    assert len(specs) == 1
    repr_specs = specs["AFL++"]
    assert len(repr_specs) == 2  # 2 builds used in fuzzing: basic and asan
    assert repr_specs["./basic/app"] == ["app1", "app2", "app3"]
    assert repr_specs["./asan/app"] == ["app4"]


def test_libfuzzer_generate_specs():
    cmdgen = LibFuzzerCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }
    _, specs = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=4,
        builds=builds,
    )
    print(specs)
    assert "libFuzzer" in specs
    assert len(specs) == 1
    repr_specs = specs["libFuzzer"]
    assert len(repr_specs) == 2  # 2 builds used in fuzzing: basic and asan
    assert repr_specs["./basic/app"] == ["out"]
    assert repr_specs["./asan/app"] == ["out"]


def test_gofuzz_generate_specs():
    cmdgen = GoFuzzCmd()
    builds = {
        BuildType.GOFUZZ: "./gofuzz/app.zip",
    }
    _, specs = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=4,
        builds=builds,
    )
    print(specs)
    assert "go-fuzz" in specs
    assert len(specs) == 1
    repr_specs = specs["go-fuzz"]
    assert len(repr_specs) == 1  # 1 build used in fuzzing
    assert repr_specs["./gofuzz/app.zip"] == ["out"]


def test_aflpp_dict():
    cmdgen = AFLplusplusCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.LAF: "./laf/app",
        BuildType.CMPLOG: "./cmplog/app",
        BuildType.ASAN: "./asan/app",
    }
    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
        dict_path="./test.dict",
    )
    print(cmds)

    for i, cmd in enumerate(cmds):
        assert (i != 0) ^ (" -x ./test.dict " in cmd)


def test_aflpp_timeout():
    cmdgen = AFLplusplusCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.LAF: "./laf/app",
        BuildType.CMPLOG: "./cmplog/app",
        BuildType.ASAN: "./asan/app",
    }
    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
        timeout_ms=1500,
    )
    print(cmds)

    for cmd in cmds:
        assert " -t 1500 " in cmd


def test_aflpp_select_default_build_type():
    """Build type not in priority list of AFL++ cmd generator."""
    cmdgen = AFLplusplusCmd()

    # no builds known to AFL++ cmd gen, select first one as default
    builds = [
        BuildType.GOFUZZ,
    ]
    assert cmdgen._select_default_build_type(builds) == BuildType.GOFUZZ


def test_aflpp_generate_cmplog_for_one_core():
    cmdgen = AFLplusplusCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.CMPLOG: "./cmplog/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=1,
        builds=builds,
    )
    print(cmds)
    helper_check_cmds(cmds, builds)
    assert "basic/app" in cmds[0]
    assert "cmplog/app" in cmds[0]
    assert " -l 2 " in cmds[0]


def test_libfuzzer_generate_all_builds():
    cmdgen = LibFuzzerCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.LAF: "./laf/app",
        BuildType.CMPLOG: "./cmplog/app",
        BuildType.ASAN: "./asan/app",
        BuildType.UBSAN: "./ubsan/app",
        BuildType.CFISAN: "./cfisan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
    )
    print(cmds)
    assert len(cmds) == 4  # basic + 3 sanitizers
    helper_check_cmds(cmds, builds)


def test_aflpp_generate_cmds_with_env():
    cmdgen = AFLplusplusCmd()

    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.UBSAN: "./ubsan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={"LD_PRELOAD": "/a/b/c.so"},
        input_corpus="in",
        output_corpus="out",
        count=6,
        builds=builds,
    )
    assert len(cmds) == 6
    for cmd in cmds:
        assert cmd.startswith("env AFL_PRELOAD=/a/b/c.so")


def test_libfuzzer_generate_cmds_with_env():
    cmdgen = LibFuzzerCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.UBSAN: "./ubsan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={"VAR": "123", "TEST": "test test"},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
    )
    print(cmds)
    assert len(cmds) == 3
    for cmd in cmds:
        assert cmd.startswith('env VAR=123 TEST="test test" ./')


def test_gofuzz_generate_cmds_with_env():
    cmdgen = GoFuzzCmd()
    builds = {
        BuildType.GOFUZZ: "./gofuzz/app.zip",
    }

    cmds, _ = cmdgen.generate(
        run_args="-func=TestFuzzFunc",
        run_env={"TEST": "test test", "VAR_1": "value1", "port": "7777"},
        input_corpus="in",
        output_corpus="testdata",
        count=8,
        builds=builds,
        timeout_ms=2500,
    )
    print(cmds)

    for cmd in cmds:
        assert cmd.startswith('env TEST="test test" VAR_1=value1 port=7777 go-fuzz ')


def test_libfuzzer_generate_few_builds():
    cmdgen = LibFuzzerCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
    )
    print(cmds)

    assert len(cmds) == 2  # basic + asan
    assert "-fork=7" in cmds[0]
    assert "-fork=1" in cmds[1]
    helper_check_cmds(cmds, builds)


def test_libfuzzer_generate_one_build():
    cmdgen = LibFuzzerCmd()
    builds_basic = {
        BuildType.BASIC: "./basic/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds_basic,
    )
    print(cmds)

    assert len(cmds) == 1
    assert "-fork=8" in cmds[0]
    helper_check_cmds(cmds, builds_basic)

    builds_asan = {
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds_asan,
    )
    print(cmds)

    assert len(cmds) == 1
    assert "-fork=8" in cmds[0]
    helper_check_cmds(cmds, builds_asan)


def test_libfuzzer_dict():
    cmdgen = LibFuzzerCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
        dict_path="./test.dict",
    )
    print(cmds)

    for cmd in cmds:
        assert " -dict=./test.dict " in cmd


def test_libfuzzer_timeout():
    cmdgen = LibFuzzerCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, _ = cmdgen.generate(
        run_args="@@",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
        timeout_ms=1500,
    )
    print(cmds)

    for cmd in cmds:
        assert " -timeout=2 " in cmd


def test_cmd_gen_not_enough_cores():
    """More sanitizers than CPU cores."""

    cmdgens = [AFLplusplusCmd(), LibFuzzerCmd()]
    builds_basic = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.UBSAN: "./ubsan/app",
        BuildType.CFISAN: "./cfisan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    for cmdgen in cmdgens:
        with pytest.raises(FuzzerCmdError):
            _, _ = cmdgen.generate(
                run_args="@@",
                run_env={},
                input_corpus="in",
                output_corpus="out",
                count=2,
                builds=builds_basic,
            )


def test_gotest_generate():
    cmdgen = GoTestCmd()
    builds = {
        BuildType.GOTEST: "./gotest/fuzz",
        BuildType.COVERAGE: "./coverage/app",  # useless build for go-test
    }

    cmds, _ = cmdgen.generate(
        run_args="-test.fuzz=FuzzParse",
        run_env={},
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds,
    )
    print(cmds)

    assert len(cmds) == 1
    cmd = cmds[0]

    assert cmd.startswith("./gotest/fuzz")
    assert "coverage/app" not in cmd
    assert " -test.fuzz=FuzzParse " in cmd
    assert ' -test.coverprofile=out/coverprofile ' in cmd
    assert " -test.parallel=8 " in cmd
    assert ' -test.fuzzcachedir=out ' in cmd
    helper_check_cmds(cmds, builds)


def test_gotest_generate_bad_run_args():
    cmdgen = GoTestCmd()
    builds = {
        BuildType.GOTEST: "./gotest/fuzz",
    }

    bad_args = [
        "@@",
        "-test.run=FuzzParse/samplename",
        "-test.fuzz=Parse",
        "",
        None,
    ]

    for ba in bad_args:
        with pytest.raises(FuzzerCmdError):
            cmdgen.generate(
                run_args=ba,
                run_env={},
                input_corpus="in",
                output_corpus="out",
                count=8,
                builds=builds,
            )


def test_gofuzz_generate():
    cmdgen = GoFuzzCmd()
    builds = {
        BuildType.GOFUZZ: "./gofuzz/app.zip",
        BuildType.COVERAGE: "./coverage/app",  # useless build for go-fuzz
    }

    cmds, _ = cmdgen.generate(
        run_args="",
        run_env={},
        input_corpus="in",
        output_corpus="testdata",
        count=8,
        builds=builds,
    )
    print(cmds)

    assert len(cmds) == 1
    assert '-bin=./gofuzz/app.zip' in cmds[0]
    assert "coverage/app" not in cmds[0]
    assert "-dumpcover" in cmds[0]
    assert "-procs=8" in cmds[0]
    assert '-workdir=testdata' in cmds[0]
    helper_check_cmds(cmds, builds)


def test_gofuzz_dict():
    cmdgen = GoFuzzCmd()
    builds = {
        BuildType.GOFUZZ: "./gofuzz/app.zip",
        BuildType.COVERAGE: "./coverage/app",  # useless build for go-fuzz
    }

    cmds, _ = cmdgen.generate(
        run_args="-func=TestFuzzFunc",
        run_env={},
        input_corpus="in",
        output_corpus="testdata",
        count=8,
        builds=builds,
        dict_path="./test.dict",
    )
    print(cmds)

    for cmd in cmds:
        assert "test.dict" not in cmd


def test_gofuzz_timeout():
    cmdgen = GoFuzzCmd()
    builds = {
        BuildType.GOFUZZ: "./gofuzz/app.zip",
        BuildType.COVERAGE: "./coverage/app",  # useless build for go-fuzz
    }

    cmds, _ = cmdgen.generate(
        run_args="-func=TestFuzzFunc",
        run_env={},
        input_corpus="in",
        output_corpus="testdata",
        count=8,
        builds=builds,
        timeout_ms=2500,
    )
    print(cmds)

    for cmd in cmds:
        assert " -timeout=3 " in cmd


def test_gofuzz_generate_bad():
    cmdgen = GoFuzzCmd()

    # only useless builds for go-fuzz
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    with pytest.raises(FuzzerCmdError):
        _, _ = cmdgen.generate(
            run_args="-func=TestFuzzFunc",
            run_env={},
            input_corpus="in",
            output_corpus="testdata",
            count=8,
            builds=builds,
        )


def test_stats_cmds():
    cmdgen = AFLplusplusCmd()

    cmd = cmdgen.stats_cmd("out")
    assert cmd is not None
    assert "afl-whatsup" in cmd
    assert "out" in cmd

    cmdgen = LibFuzzerCmd()
    assert cmdgen.stats_cmd("out") is None
    cmdgen = GoFuzzCmd()
    assert cmdgen.stats_cmd("out") is None


def helper_check_cmds(cmds: List[str], builds: Dict[BuildType, str]):
    joined = "\n".join(cmds)

    # every variable replaced
    assert "$" not in joined

    # no coverage build used in fuzz cmds
    assert "coverage/app" not in joined

    # each sanitizer only used once
    for bt in builds:
        if bt.is_static_sanitizer():
            assert joined.count(builds[bt]) == 1


def test_make_tmux_commands():
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.LAF: "./laf/app",
        BuildType.CMPLOG: "./cmplog/app",
        BuildType.ASAN: "./asan/app",
        BuildType.UBSAN: "./ubsan/app",
        BuildType.CFISAN: "./cfisan/app",
        BuildType.COVERAGE: "./coverage/app",
        BuildType.GOFUZZ: "./gofuzz/app.zip",
    }

    cmdgen_with_extra_cmds = [
        (AFLplusplusCmd(), 2),
        (LibFuzzerCmd(), 1),
        (GoFuzzCmd(), 1),
    ]

    for cmdgen, extra_cmds in cmdgen_with_extra_cmds:
        cmds, _ = cmdgen.generate(
            run_args="@@",
            run_env={},
            input_corpus="in",
            output_corpus="out",
            count=8,
            builds=builds,
        )
        stats_cmd = cmdgen.stats_cmd("out")
        tmux_cmds = make_tmux_commands([stats_cmd] + cmds, "test")

        # fuzz cmds + (stats cmd + tmux new-session cmd)
        assert len(tmux_cmds) == len(cmds) + extra_cmds

        assert all((cmd.startswith("tmux") for cmd in tmux_cmds))


def test_make_one_tmux_capture_pane_cmds():
    sess_name = "fuzz"
    index = 3

    for gen_name in FuzzerCmdFactory.registry:
        cmdgen = FuzzerCmdFactory.create(gen_name)
        cmd = cmdgen.make_one_tmux_capture_pane_cmd(sess_name, index)
        assert cmd.startswith("tmux capture-pane ")
        assert "fuzz:3" in cmd
        assert "-e" in cmd
        assert "-p" in cmd


def test_make_tmux_screen_capture_cmds():
    cmdgen = AFLplusplusCmd()
    cmds = cmdgen.make_tmux_screen_capture_cmds(
        num_fuzz_instances=32, have_stat_instance=True
    )
    assert len(cmds) == 33


def test_generate_combos_c_cxx():
    """
    Each generator shouln't fail with any valid number of cores
    """
    build_collections = {
        "basic & coverage": {
            BuildType.BASIC: "./basic/app",
            BuildType.COVERAGE: "./coverage/app",
        },
        "asan & coverage": {
            BuildType.ASAN: "./asan/app",
            BuildType.COVERAGE: "./coverage/app",
        },
        "basic, asan & coverage": {
            BuildType.BASIC: "./basic/app",
            BuildType.ASAN: "./asan/app",
            BuildType.COVERAGE: "./coverage/app",
        },
    }
    for name in FuzzerCmdFactory.registry:
        # skip go-fuzz and go-test here
        if name in ("go-fuzz", "go-test"):
            continue
        cmdgen: FuzzerCmd = FuzzerCmdFactory.create(name)
        for num_cores in range(1, 8):
            for builds_title, builds in build_collections.items():
                print(
                    f"Generator: {cmdgen.__class__.__name__}. Cores: {num_cores}. Builds: {builds_title}"
                )
                cmdgen.generate(
                    run_args="@@",
                    run_env={},
                    input_corpus="./in",
                    output_corpus="./out",
                    count=num_cores,
                    builds=builds,
                )


def test_generate_combos_gofuzz():
    """
    go-fuzz generator shouln't fail with any valid number of cores
    """
    build_collections = {
        "go-fuzz": {
            BuildType.GOFUZZ: "./gofuzz/app.zip",
        },
    }
    cmdgen: FuzzerCmd = FuzzerCmdFactory.create("go-fuzz")
    for num_cores in range(1, 8):
        for builds_title, builds in build_collections.items():
            print(
                f"Generator: {cmdgen.__class__.__name__}. Cores: {num_cores}. Builds: {builds_title}"
            )
            cmdgen.generate(
                run_args="-func=TestFuzzFunc",
                run_env={},
                input_corpus="./in",
                output_corpus="./out",
                count=num_cores,
                builds=builds,
            )
