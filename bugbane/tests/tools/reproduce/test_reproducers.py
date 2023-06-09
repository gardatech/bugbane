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
def test_factory(fuzzer_type: str, reproducer_class: Type[Reproducer]):
    assert ReproducerFactory.create(fuzzer_type).__class__ is reproducer_class


def test_factory_bad(mocker: MockerFixture):
    mocker.patch.dict(ReproducerFactory.registry, {}, clear=True)
    mocker.patch.object(ReproducerFactory, "default", None)
    with pytest.raises(TypeError):
        ReproducerFactory.create("!! unknown !!")


def test_factory_overwrite():
    class ReproducerFactoryChild(ReproducerFactory):
        registry: Dict[str, Reproducer] = {}
        default: Optional[Reproducer] = None

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
