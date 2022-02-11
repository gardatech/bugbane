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
from bugbane.modules.build_type import BuildType
from bugbane.tools.builder.builders.aflplusplus import AFLplusplusLLVMBuilder
from bugbane.tools.builder.builders.base_builders import Builder
from bugbane.tools.builder.builders.factory import FuzzBuilderFactory
from bugbane.tools.coverage.collector.factory import CoverageCollectorFactory


def test_build_type_from_str():
    mappings = {
        "basic": BuildType.BASIC,
        "LAF": BuildType.LAF,
        "cmplog": BuildType.CMPLOG,
        "Asan": BuildType.ASAN,
        "UBSAN": BuildType.UBSAN,
        "cfisAN": BuildType.CFISAN,
        "TSAN": BuildType.TSAN,
        "LSAN": BuildType.LSAN,
        "MSAN": BuildType.MSAN,
        "COvErAGE": BuildType.COVERAGE,
        "cov": BuildType.COVERAGE,
    }

    for k, v in mappings.items():
        assert v == BuildType.from_str(k)


def test_build_type_empty():
    assert BuildType.from_str("") == BuildType.BASIC
    assert BuildType.from_str(None) == BuildType.BASIC


def test_build_type_bad():
    with pytest.raises(RuntimeError):
        BuildType.from_str("!!! unknown !!!")

    # surplus space tests:
    with pytest.raises(RuntimeError):
        BuildType.from_str("ASAN ")
    with pytest.raises(RuntimeError):
        BuildType.from_str(" UBSAN")
    with pytest.raises(RuntimeError):
        BuildType.from_str(" CFISAN ")


def test_is_static_sanitizer():
    sanitizers = {
        BuildType.ASAN,
        BuildType.UBSAN,
        BuildType.CFISAN,
        BuildType.TSAN,
        BuildType.LSAN,
        BuildType.MSAN,
    }
    rest = {bt for bt in BuildType if bt not in sanitizers}

    assert all((bt.is_static_sanitizer() for bt in sanitizers))
    assert all((not bt.is_static_sanitizer() for bt in rest))


def test_assign_build_types():
    builder = AFLplusplusLLVMBuilder()
    builder.configure(
        build_cmd="./build.sh",
        build_root="/build_root",
        build_store_dir="/build_store",
        build_log_path="/var/run/test.log",
    )
    builder.assign_build_types(["ASAN"])
    assert builder.build_types == [BuildType.ASAN]


def test_assign_build_types_unique():
    builder = AFLplusplusLLVMBuilder()
    builder.configure(
        build_cmd="./build.sh",
        build_root="/build_root",
        build_store_dir="/build_store",
        build_log_path="/var/run/test.log",
    )
    types = [
        "ASAN",
        "basic",
        "cov",
        "UBSAN",
        "asan",
        "asan",
        "cmplog",
        "uBSAN",
        "COVERAGE",
        "coverage",
        "CMPlog",
        "CFISAN",
    ]
    uniq_types = {t.lower().replace("coverage", "cov") for t in types}
    uniq_len = len(uniq_types)

    builder.assign_build_types(types)
    assert uniq_len == len(builder.build_types)


def test_assign_build_types_empty():
    builder = AFLplusplusLLVMBuilder()
    builder.configure(
        build_cmd="./build.sh",
        build_root="/build_root",
        build_store_dir="/build_store",
        build_log_path="/var/run/test.log",
    )

    builder.assign_build_types([])
    assert BuildType.BASIC in builder.build_types

    builder.assign_build_types(None)
    assert BuildType.BASIC in builder.build_types


def test_ensure_build_types():
    builder = AFLplusplusLLVMBuilder()
    builder.configure(
        build_cmd="./build.sh",
        build_root="/build_root",
        build_store_dir="/build_store",
        build_log_path="/var/run/test.log",
    )

    builder.ensure_required_build_types()
    assert builder.build_types == [
        BuildType.BASIC,
        BuildType.LAF,
        BuildType.CMPLOG,
        BuildType.COVERAGE,
    ]

    builder.assign_build_types(["ASAN", "CMPLOG"])
    builder.ensure_required_build_types()
    assert builder.build_types == [
        BuildType.BASIC,
        BuildType.LAF,
        BuildType.CMPLOG,
        BuildType.ASAN,
        BuildType.COVERAGE,
    ]


def test_builder_coverage_type():
    """
    Check that each registered builder returns registered coverage type
    """
    for builder_type in FuzzBuilderFactory.registry:
        builder: Builder = FuzzBuilderFactory.create(builder_type)
        print(f"Checking {builder.__class__.__name__}")
        assert builder.get_coverage_type() in CoverageCollectorFactory.registry
