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

import pytest
from pytest_mock import MockerFixture

from bugbane.tools.corpus.minimizers.afl_cmin_minimizer import (
    AFL_cmin_Minimizer,
    MinimizerError,
)


def test_afl_cmin_not_configured(mocker: MockerFixture):
    # prevent running afl-cmin if this test breaks
    mocker.patch(
        "bugbane.modules.process.run_shell_cmd", return_value=(None, False, None)
    )
    generator = AFL_cmin_Minimizer()
    with pytest.raises(MinimizerError):
        generator.run(["1"], "2")


def test_afl_cmin_cmd_generator():
    generator = AFL_cmin_Minimizer()
    generator.configure(program="./tested", run_args=None, prog_timeout_ms=2763)

    cmd = generator._make_run_cmd(mask="samples", dest="cmin_result")
    assert cmd == "afl-cmin -t 2763 -i samples -o cmin_result -m none -- ./tested"
