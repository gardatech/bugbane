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

from bugbane.modules.stats.coverage.llvm_summary import LLVMSummaryCoverageStats
from bugbane.modules.stats.coverage.lcov import LCOVCoverageStats
from bugbane.modules.stats.coverage.go import GoCoverageStats


def test_coverage_parse_llvm():

    stats = """
Filename                      Regions    Missed Regions     Cover   Functions  Missed Functions  Executed       Lines      Missed Lines     Cover    Branches   Missed Branches     Cover
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
include/funcs.h                     3                 2    33.33%           3                 2    33.33%           9                 6    33.33%           0                 0         -
src/fuzzable_app.cpp               33                 6    81.82%           3                 0   100.00%          71                14    80.28%          26                 6    76.92%
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
TOTAL                              36                 8    77.78%           6                 2    66.67%          80                20    75.00%          26                 6    76.92%
"""

    cov_stats = LLVMSummaryCoverageStats()
    cov_info = cov_stats.read_from_str(stats)

    assert cov_info["bb_cover"] == 20
    assert cov_info["bb_total"] == 26

    assert cov_info["line_cover"] == 60
    assert cov_info["line_total"] == 80

    assert cov_info["func_cover"] == 4
    assert cov_info["func_total"] == 6


def test_llvm_coverage_init():
    stats = LLVMSummaryCoverageStats()
    assert stats.bb_total is None
    assert stats.bb_cover is None
    assert stats.line_total is None
    assert stats.line_cover is None
    assert stats.func_total is None
    assert stats.func_cover is None


def test_llvm_coverage_percent():
    stats = LLVMSummaryCoverageStats(
        bb_cover=1,
        bb_total=2,
        line_cover=3,
        line_total=4,
        func_cover=111,
        func_total=444,
    )

    assert stats.bb_cover_percent == 50.0
    assert stats.line_cover_percent == 75.0
    assert stats.func_cover_percent == 25.0


def test_llvm_coverage_overflow():
    stats = LLVMSummaryCoverageStats(
        line_cover=100,
        line_total=5,
    )

    assert stats.line_cover_percent == 100.0


def test_llvm_coverage_zero_division():
    stats = LLVMSummaryCoverageStats(
        line_total=0, line_cover=1, func_total=1, func_cover=0
    )

    assert stats.line_cover_percent == 100.0
    assert stats.func_cover_percent == 0.0


def test_llvm_coverage_bb_is_optional():
    stats = LLVMSummaryCoverageStats()
    assert stats.bb_cover_percent is None

    stats = LLVMSummaryCoverageStats(bb_cover=1)
    assert stats.bb_cover_percent is None

    stats = LLVMSummaryCoverageStats(bb_total=1)
    assert stats.bb_cover_percent is None


def test_llvm_coverage_sum():
    totals = LLVMSummaryCoverageStats()

    coverage1 = LLVMSummaryCoverageStats(
        line_cover=30,
        line_total=40,
        func_cover=1000,
        func_total=2000,
    )

    totals.add_stats_from(coverage1)

    assert totals.num_reports == 1
    assert totals.bb_cover is None
    assert totals.bb_total is None
    assert totals.line_cover == 30
    assert totals.line_total == 40
    assert totals.func_cover == 1000
    assert totals.func_total == 2000

    coverage2 = LLVMSummaryCoverageStats(
        bb_cover=1,
        bb_total=2,
        line_cover=3,
        line_total=4,
        func_cover=111,
        func_total=222,
    )

    totals.add_stats_from(coverage2)

    assert totals.num_reports == 2
    assert totals.bb_cover == 1
    assert totals.bb_total == 2
    assert totals.line_cover == 33
    assert totals.line_total == 44
    assert totals.func_cover == 1111
    assert totals.func_total == 2222


def test_coverage_parse_lcov():

    stats = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">

<html lang="en">

<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>LCOV - cov.info</title>
  <link rel="stylesheet" type="text/css" href="gcov.css">
</head>

<body>

  <table width="100%" border=0 cellspacing=0 cellpadding=0>
    <tr><td class="title">LCOV - code coverage report</td></tr>
    <tr><td class="ruler"><img src="glass.png" width=3 height=3 alt=""></td></tr>

    <tr>
      <td width="100%">
        <table cellpadding=1 border=0 width="100%">
          <tr>
            <td width="10%" class="headerItem">Current view:</td>
            <td width="35%" class="headerValue">top level</td>
            <td width="5%"></td>
            <td width="15%"></td>
            <td width="10%" class="headerCovTableHead">Hit</td>
            <td width="10%" class="headerCovTableHead">Total</td>
            <td width="15%" class="headerCovTableHead">Coverage</td>
          </tr>
          <tr>
            <td class="headerItem">Test:</td>
            <td class="headerValue">cov.info</td>
            <td></td>
            <td class="headerItem">Lines:</td>
            <td class="headerCovTableEntry">1942</td>
            <td class="headerCovTableEntry">7073</td>
            <td class="headerCovTableEntryLo">27.5 %</td>
          </tr>
          <tr>
            <td class="headerItem">Date:</td>
            <td class="headerValue">2021-12-08 15:17:02</td>
            <td></td>
            <td class="headerItem">Functions:</td>
            <td class="headerCovTableEntry">387</td>
            <td class="headerCovTableEntry">809</td>
            <td class="headerCovTableEntryLo">47.8 %</td>
          </tr>
          <tr>
            <td></td>
            <td></td>
            <td></td>
            <td class="headerItem">Branches:</td>
            <td class="headerCovTableEntry">941</td>
            <td class="headerCovTableEntry">7260</td>
            <td class="headerCovTableEntryLo">13.0 %</td>
          </tr>
          <tr><td><img src="glass.png" width=3 height=3 alt=""></td></tr>
        </table>
      </td>
    </tr>

    <tr><td class="ruler"><img src="glass.png" width=3 height=3 alt=""></td></tr>
  </table>

  <center>
  <table width="80%" cellpadding=1 cellspacing=1 border=0>

    <tr>
      <td width="44%"><br></td>
      <td width="8%"></td>
      <td width="8%"></td>
      <td width="8%"></td>
      <td width="8%"></td>
      <td width="8%"></td>
      <td width="8%"></td>
      <td width="8%"></td>
    </tr>

    <tr>
      <td class="tableHead">Directory <span class="tableHeadSort"><img src="glass.png" width=10 height=14 alt="Sort by name" title="Sort by name" border=0></span></td>
      <td class="tableHead" colspan=3>Line Coverage <span class="tableHeadSort"><a href="index-sort-l.html"><img src="updown.png" width=10 height=14 alt="Sort by line coverage" title="Sort by line coverage" border=0></a></span></td>
      <td class="tableHead" colspan=2>Functions <span class="tableHeadSort"><a href="index-sort-f.html"><img src="updown.png" width=10 height=14 alt="Sort by function coverage" title="Sort by function coverage" border=0></a></span></td>
      <td class="tableHead" colspan=2>Branches <span class="tableHeadSort"><a href="index-sort-b.html"><img src="updown.png" width=10 height=14 alt="Sort by branch coverage" title="Sort by branch coverage" border=0></a></span></td>
    </tr>
    <tr>
      <td class="coverFile"><a href="re2/index.html">re2</a></td>
      <td class="coverBar" align="center">
        <table border=0 cellspacing=0 cellpadding=1><tr><td class="coverBarOutline"><img src="ruby.png" width=28 height=10 alt="27.5%"><img src="snow.png" width=72 height=10 alt="27.5%"></td></tr></table>
      </td>
      <td class="coverPerLo">27.5&nbsp;%</td>
      <td class="coverNumLo">1853 / 6732</td>
      <td class="coverPerLo">48.0&nbsp;%</td>
      <td class="coverNumLo">368 / 767</td>
      <td class="coverPerLo">12.7&nbsp;%</td>
      <td class="coverNumLo">888 / 6982</td>
    </tr>
    <tr>
      <td class="coverFile"><a href="re2/fuzzing/index.html">re2/fuzzing</a></td>
      <td class="coverBar" align="center">
        <table border=0 cellspacing=0 cellpadding=1><tr><td class="coverBarOutline"><img src="ruby.png" width=62 height=10 alt="61.7%"><img src="snow.png" width=38 height=10 alt="61.7%"></td></tr></table>
      </td>
      <td class="coverPerLo">61.7&nbsp;%</td>
      <td class="coverNumLo">74 / 120</td>
      <td class="coverPerLo">66.7&nbsp;%</td>
      <td class="coverNumLo">8 / 12</td>
      <td class="coverPerLo">33.1&nbsp;%</td>
      <td class="coverNumLo">46 / 139</td>
    </tr>
    <tr>
      <td class="coverFile"><a href="util/index.html">util</a></td>
      <td class="coverBar" align="center">
        <table border=0 cellspacing=0 cellpadding=1><tr><td class="coverBarOutline"><img src="ruby.png" width=7 height=10 alt="6.8%"><img src="snow.png" width=93 height=10 alt="6.8%"></td></tr></table>
      </td>
      <td class="coverPerLo">6.8&nbsp;%</td>
      <td class="coverNumLo">15 / 221</td>
      <td class="coverPerLo">36.7&nbsp;%</td>
      <td class="coverNumLo">11 / 30</td>
      <td class="coverPerLo">5.0&nbsp;%</td>
      <td class="coverNumLo">7 / 139</td>
    </tr>
  </table>
  </center>
  <br>

  <table width="100%" border=0 cellspacing=0 cellpadding=0>
    <tr><td class="ruler"><img src="glass.png" width=3 height=3 alt=""></td></tr>
    <tr><td class="versionInfo">Generated by: <a href="http://ltp.sourceforge.net/coverage/lcov.php">LCOV version 1.15</a></td></tr>
  </table>
  <br>

</body>
</html>
"""

    cov_stats = LCOVCoverageStats()
    cov_info = cov_stats.read_from_str(stats)

    assert cov_info["bb_cover"] == 941
    assert cov_info["bb_total"] == 7260

    assert cov_info["line_cover"] == 1942
    assert cov_info["line_total"] == 7073

    assert cov_info["func_cover"] == 387
    assert cov_info["func_total"] == 809


def test_coverage_parse_go():
    stats = """/src/go/fuzz.go:5:      Fuzz            100.0%
/src/go/fuzzable.go:7:  check_index     50.0%
/src/go/fuzzable.go:13: recursive_sum   62.5%
/src/go/fuzzable.go:27: busy_loop       68.8%
/src/go/fuzzable.go:52: Parse           80.0%
total:                  (statements)    70.3%
    """

    cov_stats = GoCoverageStats()
    cov_info = cov_stats.read_from_str(stats)

    # go tool cover provides no counts,
    # value 10000 was arbitrarily chosen in parsing code

    assert cov_info["line_total"] == 10000
    assert cov_info["line_cover"] == 7030


def test_coverage_sum_different():
    """Sum coverage stats from different subclasses of CoverageStats"""

    totals = LLVMSummaryCoverageStats(
        num_reports=1,
        line_cover=30,
        line_total=40,
        func_cover=1000,
        func_total=2000,
    )

    coverage2 = GoCoverageStats(
        line_cover=3,
        line_total=4,
    )

    totals.add_stats_from(coverage2)

    assert totals.num_reports == 2
    assert totals.bb_cover is None
    assert totals.bb_total is None
    assert totals.line_cover == 33
    assert totals.line_total == 44
    assert totals.func_cover == 1000
    assert totals.func_total == 2000

    coverage3 = LCOVCoverageStats(
        bb_cover=1,
        bb_total=2,
        line_cover=33,
        line_total=44,
        func_cover=10,
        func_total=20,
    )

    totals.add_stats_from(coverage3)

    assert totals.num_reports == 3
    assert totals.bb_cover == 1
    assert totals.bb_total == 2
    assert totals.line_cover == 66
    assert totals.line_total == 88
    assert totals.func_cover == 1010
    assert totals.func_total == 2020
