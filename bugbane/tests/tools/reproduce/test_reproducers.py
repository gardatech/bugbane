# Copyright 2022-2025 Garda Technologies, LLC. All rights reserved.
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

from typing import Dict, Optional, Type

import pytest
from pytest_mock import MockerFixture

from bugbane.tools.reproduce.reproducers.factory import ReproducerFactory
from bugbane.tools.reproduce.reproducers.reproducer import Reproducer
from bugbane.tools.reproduce.reproducers.default_reproducer import DefaultReproducer
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
