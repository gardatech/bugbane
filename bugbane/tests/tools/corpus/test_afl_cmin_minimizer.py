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

from bugbane.tools.corpus.minimizers.afl_cmin_minimizer import (
    AFL_cmin_Minimizer,
    MinimizerError,
)


def test_post_process_afl_cmin_output():
    output = """1
2
3
4
5
"""
    result = AFL_cmin_Minimizer.post_process_afl_cmin_output(output, display_limit=4)
    assert result == "1\n2\n<...>\n4\n5\n"

    result = AFL_cmin_Minimizer.post_process_afl_cmin_output(output, display_limit=2)
    assert result == "1\n<...>\n5\n"

    with pytest.raises(MinimizerError):
        AFL_cmin_Minimizer.post_process_afl_cmin_output(output, display_limit=1)

    result = AFL_cmin_Minimizer.post_process_afl_cmin_output(output, display_limit=100)
    assert result == "1\n2\n3\n4\n5\n"
