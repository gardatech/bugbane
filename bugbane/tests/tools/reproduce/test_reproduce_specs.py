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

from bugbane.tools.reproduce.main import dict_to_reproduce_specs


def test_dict_to_reproduce_specs():
    fuzz_sync_dir = "out"
    reproduce_specs_dict = {
        "AFL++": {"./basic/app": ["app1", "app2", "app3"], "./asan/app": ["app4"]}
    }
    expected = [
        [
            "AFL++:out",
            "./basic/app:app1",
            "./basic/app:app2",
            "./basic/app:app3",
            "./asan/app:app4",
        ]
    ]

    specs = dict_to_reproduce_specs(fuzz_sync_dir, reproduce_specs_dict)
    assert specs == expected
