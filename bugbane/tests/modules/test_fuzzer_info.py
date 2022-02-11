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

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo
from bugbane.modules.fuzzer_info.aflplusplus import AFLplusplusInfo
from bugbane.modules.fuzzer_info.libfuzzer import LibFuzzerInfo
from bugbane.modules.fuzzer_info.gofuzz import GoFuzzInfo


def test_factory():
    paths: FuzzerInfo = FuzzerInfoFactory.create("AFL++")
    assert paths.__class__ is AFLplusplusInfo

    paths: FuzzerInfo = FuzzerInfoFactory.create("libFuzzer")
    assert paths.__class__ is LibFuzzerInfo

    paths: FuzzerInfo = FuzzerInfoFactory.create("go-fuzz")
    assert paths.__class__ is GoFuzzInfo


def test_afl():
    paths = AFLplusplusInfo()
    assert paths.initial_samples_required()
    assert paths.input_dir("./out") == "in"

    assert paths.sample_mask("./out", "*") == "./out/*/queue/id*"
    assert paths.sample_mask("./out", "default") == "./out/default/queue/id*"

    assert paths.crash_mask("./out", "*") == "./out/*/crashes/id*"
    assert paths.crash_mask("./out", "m1") == "./out/m1/crashes/id*"

    assert paths.hang_mask("./out", "*") == "./out/*/hangs/id*"
    assert paths.hang_mask("./out", "s257") == "./out/s257/hangs/id*"

    assert paths.stats_dir("/fuzz/out") == "/fuzz/out"
    assert paths.stats_dir("out/") == "out/"


def test_libfuzzer():
    """
    unlike AFL-like fuzzers, libFuzzer doesn't use fuzzer names and subfolders
    """

    paths = LibFuzzerInfo()
    assert not paths.initial_samples_required()
    assert paths.input_dir("./out") == "./out"

    assert paths.sample_mask("./out", "*") == "./out/*"
    assert paths.sample_mask("./out", "default") == "./out/*"

    assert paths.crash_mask("./out", "*") == "artifacts/crash-*"
    assert paths.crash_mask("./out", "m1") == "artifacts/crash-*"

    assert paths.hang_mask("./out", "*") == "artifacts/timeout-*"
    assert paths.hang_mask("./out", "s257") == "artifacts/timeout-*"

    assert paths.stats_dir("/fuzz/out") == "/fuzz"
    assert paths.stats_dir("out/") == "out/.."


def test_gofuzz():
    paths = GoFuzzInfo()
    assert not paths.initial_samples_required()
    assert paths.input_dir("./out") == "./out/corpus"

    assert paths.sample_mask("./out", "*") == "./out/corpus/*"
    assert paths.sample_mask("./out", "default") == "./out/corpus/*"

    assert paths.crash_mask("./out", "*").startswith("./out/crashers/*")
    assert paths.crash_mask("./out", "m1").startswith("./out/crashers/*")

    assert paths.hang_mask("./out", "*").startswith("./out/crashers/*")
    assert paths.hang_mask("./out", "s257").startswith("./out/crashers/*")

    assert paths.stats_dir("/fuzz/out") == "/fuzz"
    assert paths.stats_dir("out/") == "out/.."
