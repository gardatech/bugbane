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

import pytest

from bugbane.modules.stats.coverage.factory import CoverageStatsFactory
from bugbane.modules.stats.coverage.llvm_summary import LLVMSummaryCoverageStats

from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory
from bugbane.modules.stats.fuzz.aflplusplus import AFLplusplusFuzzStats
from bugbane.modules.stats.fuzz.libfuzzer import LibFuzzerFuzzStats

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_cmd.factory import FuzzerCmdFactory


def test_cov_stats_factory_ok():
    llvm_summary = CoverageStatsFactory.create("llvm-summary")
    assert llvm_summary.__class__ is LLVMSummaryCoverageStats


def test_cov_stats_factory_exception():
    with pytest.raises(TypeError):
        CoverageStatsFactory.create("!!! unknown !!! factory !!!")


def test_fuzz_stats_factory_ok():
    aflpp = FuzzStatsFactory.create("AFL++")
    assert aflpp.__class__ is AFLplusplusFuzzStats

    libfuzzer = FuzzStatsFactory.create("libFuzzer")
    assert libfuzzer.__class__ is LibFuzzerFuzzStats


def test_fuzz_stats_factory_exception():
    with pytest.raises(TypeError):
        FuzzStatsFactory.create("!!! unknown !!! factory !!!")


def test_registries_are_not_shared():
    assert FuzzStatsFactory.registry is not CoverageStatsFactory.registry


def test_factories_are_consistent():
    cmds = set(FuzzerCmdFactory.registry)
    paths = set(FuzzerInfoFactory.registry)
    fuzz_stats = set(FuzzStatsFactory.registry)
    print("FuzzerCmdFactory  : ", cmds)
    print("FuzzInfoFactory   : ", paths)
    print("FuzzStatsFactory  : ", fuzz_stats)
    assert cmds == paths
    assert cmds == fuzz_stats
