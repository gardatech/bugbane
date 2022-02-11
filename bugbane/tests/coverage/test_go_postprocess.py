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

from bs4 import BeautifulSoup

from bugbane.tools.coverage.collector.go import GoCoverageCollector


def test_postprocess():
    html = """<!DOCTYPE html>
<html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
		<title>go: Go Coverage Report</title>
		<style>
			body {
				background: black;
				color: rgb(80, 80, 80);
			}
			body, pre, #legend span {
				font-family: Menlo, monospace;
				font-weight: bold;
			}
			#topbar {
				background: black;
				position: fixed;
				top: 0; left: 0; right: 0;
				height: 42px;
				border-bottom: 1px solid rgb(80, 80, 80);
			}
			#content {
				margin-top: 50px;
			}
			#nav, #legend {
				float: left;
				margin-left: 10px;
			}
			#legend {
				margin-top: 12px;
			}
			#nav {
				margin-top: 10px;
			}
			#legend span {
				margin: 0 5px;
			}
			.cov0 { color: rgb(192, 0, 0) }
.cov1 { color: rgb(128, 128, 128) }
.cov2 { color: rgb(116, 140, 131) }
.cov3 { color: rgb(104, 152, 134) }
.cov4 { color: rgb(92, 164, 137) }
.cov5 { color: rgb(80, 176, 140) }
.cov6 { color: rgb(68, 188, 143) }
.cov7 { color: rgb(56, 200, 146) }
.cov8 { color: rgb(44, 212, 149) }
.cov9 { color: rgb(32, 224, 152) }
.cov10 { color: rgb(20, 236, 155) }

		</style>
	</head>
	<body>
    <p>background: black;</p>
    </body>
</html>
"""
    collector = GoCoverageCollector()
    new_html = collector._post_process_html_string(html)
    soup = BeautifulSoup(new_html, "lxml")
    print(str(soup))

    style = soup.find("style").text
    assert "background: black;" not in style

    # replacements should only occur in style section
    body = soup.find("body").text
    assert "background: black;" in body
