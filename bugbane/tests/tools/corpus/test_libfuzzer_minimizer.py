# Copyright 2022-2024 Garda Technologies, LLC. All rights reserved.
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

from bugbane.tools.corpus.minimizers.libfuzzer_minimizer import (
    LibFuzzerMinimizer,
    MinimizerError,
)


def test_make_run_cmd() -> None:
    cmin = LibFuzzerMinimizer()
    cmin.program = "./myprog"
    cmin.prog_timeout_ms = 234
    assert (
        cmin._make_run_cmd(input_dir="samples/", dest_dir="minimized")
        == '"./myprog" -merge=1 -rss_limit_mb=0 -timeout=1 "minimized" "samples/"'
    )

def test_libfuzzer_not_configured_with_program(mocker: MockerFixture) -> None:
    # prevent running afl-cmin if this test breaks
    mocker.patch(
        "bugbane.modules.process.run_shell_cmd", return_value=(None, False, None)
    )
    generator = LibFuzzerMinimizer()
    with pytest.raises(MinimizerError, match="not configured with program"):
        generator.run(["1"], "2")
