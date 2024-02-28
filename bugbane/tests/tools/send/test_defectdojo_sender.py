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

from typing import Iterable
import pytest

from bugbane.tools.send.dd_api.abc import DefectDojoAPI
from bugbane.tools.send.defectdojo_sender import DefectDojoSender


@pytest.mark.parametrize(
    "tsp, old_path, new_path",
    [
        (["old->new"], "/old/mysample", "/new/mysample"),
        (["nonexistent->new"], "/old/mysample", "/old/mysample"),
        (["/old/->../new/"], "/old/mysample", "../new/mysample"),
        (["/old/->"], "/old/mysample", "mysample"),
        (["->new/"], "mysample", "new/mysample"),
        (["->"], "mysample", "mysample"),  # ignored, as both sides are empty
    ],
)
def test_translate_sample_path(
    tsp: Iterable[str], old_path: str, new_path: str
) -> None:
    api: DefectDojoAPI = None  # pyright: ignore
    sender = DefectDojoSender(
        api=api, cards_file_path="", translate_sample_paths_arg=tsp
    )
    assert sender.translate_sample_path(path=old_path) == new_path
