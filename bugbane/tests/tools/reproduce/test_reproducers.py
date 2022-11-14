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

from typing import Dict, Optional

import pytest
from pytest_mock import MockerFixture

from bugbane.tools.reproduce.reproducers.factory import ReproducerFactory
from bugbane.tools.reproduce.reproducers.reproducer import Reproducer
from bugbane.tools.reproduce.reproducers.default_reproducer import DefaultReproducer
from bugbane.tools.reproduce.reproducers.gofuzz import GoFuzzReproducer
from bugbane.tools.reproduce.reproducers.gotest import GoTestReproducer


def test_factory():
    assert ReproducerFactory.create("AFL++").__class__ is DefaultReproducer
    assert ReproducerFactory.create("libFuzzer").__class__ is DefaultReproducer
    assert ReproducerFactory.create("go-fuzz").__class__ is GoFuzzReproducer
    assert ReproducerFactory.create("go-test").__class__ is GoTestReproducer


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


def test_gotest_make_reproduce_cmd():
    r = GoTestReproducer()

    inp_exp = [
        (
            "testdata/fuzz/FuzzParse/beefbeefbeef",
            "-test.run=FuzzParse/beefbeefbeef",
        ),
        (
            "/fuzz/myapp/testdata/fuzz/FuzzSimpleParse/beefbeefbeef",
            "-test.run=FuzzSimpleParse/beefbeefbeef",
        ),
    ]

    for (inp, exp) in inp_exp:
        print(f"{inp=}, {exp=}")
        assert r.prep_run_args(sample_path=inp) == exp
