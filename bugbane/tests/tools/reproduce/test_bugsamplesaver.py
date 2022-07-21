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

from typing import Dict

from bugbane.tools.reproduce.bugsamplesaver import BugSampleSaver, BugSampleSaverError


def test_title_to_sample_name():
    in_out = [
        (
            "Crash in LibName::Method at /opt/libname/src/parse.cpp:432",
            "crash_in_libname_method_at_opt_libname_src_parse_cpp_432",
        ),
    ]

    bss = BugSampleSaver()

    for inp, exp in in_out:
        assert bss.title_to_sample_name(inp) == exp
