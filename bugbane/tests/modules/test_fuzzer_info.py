# Copyright 2022-2023 Garda Technologies, LLC. All rights reserved.
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

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo
from bugbane.modules.fuzzer_info.aflplusplus import AFLplusplusInfo
from bugbane.modules.fuzzer_info.libfuzzer import LibFuzzerInfo
from bugbane.modules.fuzzer_info.gofuzz import GoFuzzInfo
from bugbane.modules.fuzzer_info.gotest import GoTestInfo


def test_factory():
    info: FuzzerInfo = FuzzerInfoFactory.create("AFL++")
    assert info.__class__ is AFLplusplusInfo

    info: FuzzerInfo = FuzzerInfoFactory.create("libFuzzer")
    assert info.__class__ is LibFuzzerInfo

    info: FuzzerInfo = FuzzerInfoFactory.create("go-fuzz")
    assert info.__class__ is GoFuzzInfo

    info: FuzzerInfo = FuzzerInfoFactory.create("go-test")
    assert info.__class__ is GoTestInfo


def test_afl():
    info = AFLplusplusInfo()
    assert info.initial_samples_required()
    assert info.input_dir("./out") == "in"

    assert info.sample_mask("./out", "*") == "./out/*/queue/id*"
    assert info.sample_mask("./out", "default") == "./out/default/queue/id*"

    assert info.crash_mask("./out", "*") == "./out/*/crashes/id*"
    assert info.crash_mask("./out", "m1") == "./out/m1/crashes/id*"

    assert info.hang_mask("./out", "*") == "./out/*/hangs/id*"
    assert info.hang_mask("./out", "s257") == "./out/s257/hangs/id*"

    assert info.stats_dir("/fuzz/out") == "/fuzz/out"
    assert info.stats_dir("out/") == "out/"
    assert info.coverage_dir("out/") is None

    assert info.can_continue_after_bug() is True


def test_libfuzzer():
    """
    unlike AFL-like fuzzers, libFuzzer doesn't use fuzzer names and subfolders
    """

    info = LibFuzzerInfo()
    assert not info.initial_samples_required()
    assert info.input_dir("./out") == "./out"

    assert info.sample_mask("./out", "*") == "./out/*"
    assert info.sample_mask("./out", "default") == "./out/*"

    assert info.crash_mask("./out", "*") == "artifacts/crash-*"
    assert info.crash_mask("./out", "m1") == "artifacts/crash-*"

    assert info.hang_mask("./out", "*") == "artifacts/timeout-*"
    assert info.hang_mask("./out", "s257") == "artifacts/timeout-*"

    assert info.stats_dir("/fuzz/out") == "/fuzz"
    assert info.stats_dir("out/") == "out/.."
    assert info.coverage_dir("out/") is None

    assert info.can_continue_after_bug() is True


def test_gofuzz():
    info = GoFuzzInfo()
    assert not info.initial_samples_required()
    assert info.input_dir("./out") == "./out/corpus"

    assert info.sample_mask("./out", "*") == "./out/corpus/*"
    assert info.sample_mask("./out", "default") == "./out/corpus/*"

    assert info.crash_mask("./out", "*").startswith("./out/crashers/*")
    assert info.crash_mask("./out", "m1").startswith("./out/crashers/*")

    assert info.hang_mask("./out", "*").startswith("./out/crashers/*")
    assert info.hang_mask("./out", "s257").startswith("./out/crashers/*")

    assert info.stats_dir("/fuzz/out") == "/fuzz"
    assert info.stats_dir("out/") == "out/.."
    assert info.coverage_dir("out/") == "out/"

    assert info.can_continue_after_bug() is True


def test_gotest():
    info = GoTestInfo()
    assert not info.initial_samples_required()
    assert info.input_dir("./out") == "./out/corpus"

    assert info.sample_mask("./out", "*") == "./out/*/*"
    assert info.sample_mask("./out", "default") == "./out/*/*"

    assert info.crash_mask("./out", "*") == "testdata/fuzz/*/*"
    assert info.crash_mask("./out", "m1") == "testdata/fuzz/*/*"

    assert info.hang_mask("./out", "*") == ""
    assert info.hang_mask("./out", "m1") == ""

    assert info.stats_dir("/fuzz/out") == "/fuzz"
    assert info.stats_dir("out/") == "out/.."
    assert info.coverage_dir("out/") == "out/"

    assert info.can_continue_after_bug() is False
