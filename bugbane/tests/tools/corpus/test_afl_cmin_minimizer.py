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

from bugbane.tools.corpus.minimizers.afl_cmin_minimizer import (
    AFL_cmin_Minimizer,
    MinimizerError,
)



afl_cmin_output = """1
2
3
4
5
"""


@pytest.mark.parametrize(
    "display_limit, expected_output",
    [
        (4, "1\n2\n<...>\n4\n5\n"),
        (2, "1\n<...>\n5\n"),
        (100, "1\n2\n3\n4\n5\n"),
    ],
)
def test_post_process_afl_cmin_output(display_limit: int, expected_output: str) -> None:
    result = AFL_cmin_Minimizer.post_process_afl_cmin_output(
        afl_cmin_output, display_limit=display_limit
    )
    assert result == expected_output


def test_post_process_afl_cmin_output_bad() -> None:
    with pytest.raises(MinimizerError):
        AFL_cmin_Minimizer.post_process_afl_cmin_output(
            afl_cmin_output, display_limit=1
        )


def test_make_run_cmd() -> None:
    cmin = AFL_cmin_Minimizer()
    cmin.program = "./myprog"
    cmin.prog_timeout_ms = 234
    assert (
        cmin._make_run_cmd(input_dir="samples/", dest_dir="minimized")
        == 'afl-cmin -t 234 -i "samples/" -o "minimized" -m none -- "./myprog"'
    )

def test_afl_cmin_not_configured_with_program(mocker: MockerFixture) -> None:
    # prevent running afl-cmin if this test breaks
    mocker.patch(
        "bugbane.modules.process.run_shell_cmd", return_value=(None, False, None)
    )
    generator = AFL_cmin_Minimizer()
    with pytest.raises(MinimizerError, match="not configured with program"):
        generator.run(["1"], "2")
