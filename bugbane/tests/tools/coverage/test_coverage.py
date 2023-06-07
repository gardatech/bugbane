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

from bugbane.tools.coverage.collector.go import GoCoverageCollector


def test_go_filter():
    collector = GoCoverageCollector()
    contents = """mode: set
/usr/lib/go/src/fmt/scan.go:197.3,198.1 0 0
/src/go/fuzzable.go:56.2,57.15 2 1
/usr/lib/go/src/reflect/type.go:1839.2,1840.13 2 0
/src/go/fuzzable.go:60.2,61.13 2 1
"""
    lines = contents.splitlines()

    collector.src_root = "/src/go"

    expected = [
        "mode: set",
        "/src/go/fuzzable.go:56.2,57.15 2 1",
        "/src/go/fuzzable.go:60.2,61.13 2 1",
    ]
    assert collector._filter_cov_file_lines(lines) == expected


def test_go_filter_no_src_root():
    collector = GoCoverageCollector()
    contents = """mode: set
/usr/lib/go/src/fmt/scan.go:197.3,198.1 0 0
/src/go/fuzzable.go:56.2,57.15 2 1
/usr/lib/go/src/reflect/type.go:1839.2,1840.13 2 0
/src/go/fuzzable.go:60.2,61.13 2 1
"""
    lines = contents.splitlines()

    collector.src_root = None

    expected = [
        "mode: set",
        "/usr/lib/go/src/fmt/scan.go:197.3,198.1 0 0",
        "/src/go/fuzzable.go:56.2,57.15 2 1",
        "/usr/lib/go/src/reflect/type.go:1839.2,1840.13 2 0",
        "/src/go/fuzzable.go:60.2,61.13 2 1",
    ]
    assert collector._filter_cov_file_lines(lines) == expected
