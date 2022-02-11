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

from bugbane.modules.build_type import BuildType
from bugbane.modules.string_utils import replace_part_in_str_list
from bugbane.tools.fuzz.command_utils import make_tmux_commands
from bugbane.modules.fuzzer_cmd.factory import FuzzerCmdFactory
from bugbane.modules.fuzzer_cmd.fuzzer_cmd import FuzzerCmd
from bugbane.modules.fuzzer_cmd.aflplusplus import AFLplusplusCmd
from bugbane.modules.fuzzer_cmd.libfuzzer import LibFuzzerCmd
from bugbane.modules.fuzzer_cmd.gofuzz import GoFuzzCmd


def test_generate_commands():
    cmdgen = AFLplusplusCmd()

    cmd = cmdgen.generate_one("in", "out")
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

    cmds, specs = cmdgen.generate(
        run_args="@@", input_corpus="in", output_corpus="out", count=17, builds=builds
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


def test_aflpp_generate():
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

    cmds, specs = cmdgen.generate(
        run_args="@@", input_corpus="in", output_corpus="out", count=8, builds=builds
    )
    print(cmds)
    print(specs)
    helper_check_cmds(cmds, builds)


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

    cmds, specs = cmdgen.generate(
        run_args="@@", input_corpus="in", output_corpus="out", count=8, builds=builds
    )
    print(cmds)
    print(specs)
    assert len(cmds) == 4  # basic + 3 sanitizers
    helper_check_cmds(cmds, builds)


def test_libfuzzer_generate_few_builds():
    cmdgen = LibFuzzerCmd()
    builds = {
        BuildType.BASIC: "./basic/app",
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, specs = cmdgen.generate(
        run_args="@@", input_corpus="in", output_corpus="out", count=8, builds=builds
    )
    print(cmds)
    print(specs)

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

    cmds, specs = cmdgen.generate(
        run_args="@@",
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds_basic,
    )
    print(cmds)
    print(specs)

    assert len(cmds) == 1
    assert "-fork=8" in cmds[0]
    helper_check_cmds(cmds, builds_basic)

    builds_asan = {
        BuildType.ASAN: "./asan/app",
        BuildType.COVERAGE: "./coverage/app",
    }

    cmds, specs = cmdgen.generate(
        run_args="@@",
        input_corpus="in",
        output_corpus="out",
        count=8,
        builds=builds_asan,
    )
    print(cmds)
    print(specs)

    assert len(cmds) == 1
    assert "-fork=8" in cmds[0]
    helper_check_cmds(cmds, builds_asan)


def test_gofuzz_generate_one_build():
    cmdgen = GoFuzzCmd()
    builds = {
        BuildType.GOFUZZ: "./gofuzz/app.zip",
        BuildType.COVERAGE: "./coverage/app",  # useless build for go-fuzz
    }

    cmds, specs = cmdgen.generate(
        run_args="-func=TestFuzzFunc",
        input_corpus="in",
        output_corpus="testdata",
        count=8,
        builds=builds,
    )
    print(cmds)
    print(specs)

    assert len(cmds) == 1
    assert "-bin=./gofuzz/app.zip" in cmds[0]
    assert "-dumpcover" in cmds[0]
    assert "-procs=8" in cmds[0]
    assert "-workdir=testdata" in cmds[0]
    assert "-func=TestFuzzFunc" in cmds[0]
    helper_check_cmds(cmds, builds)


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

    cmds, specs = cmdgen.generate(
        run_args="@@", input_corpus="in", output_corpus="out", count=8, builds=builds
    )
    stats_cmd = cmdgen.stats_cmd("out")
    tmux_cmds = make_tmux_commands([stats_cmd] + cmds, "test")

    # fuzz cmds + stats cmd + tmux new-session cmd
    assert len(tmux_cmds) == len(cmds) + 2

    assert all((cmd.startswith("tmux") for cmd in tmux_cmds))


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
        # skip go-fuzz here
        if name == "go-fuzz":
            continue
        cmdgen: FuzzerCmd = FuzzerCmdFactory.create(name)
        for num_cores in range(1, 8):
            for builds_title, builds in build_collections.items():
                print(
                    f"Generator: {cmdgen.__class__.__name__}. Cores: {num_cores}. Builds: {builds_title}"
                )
                cmdgen.generate(
                    run_args="@@",
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
                input_corpus="./in",
                output_corpus="./out",
                count=num_cores,
                builds=builds,
            )
