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

from io import BytesIO, StringIO

from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats
from bugbane.modules.stats.fuzz.aflplusplus import AFLplusplusFuzzStats
from bugbane.modules.stats.fuzz.libfuzzer import LibFuzzerFuzzStats
from bugbane.modules.stats.fuzz.gofuzz import GoFuzzFuzzStats
from bugbane.modules.stats.fuzz.gotest import GoTestFuzzStats
from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory

MOCK_FILE_UTILS_OPEN = "bugbane.modules.file_utils.open"
MOCK_FILE_UTILS_OS_PATH_GETSIZE = "bugbane.modules.file_utils.os.path.getsize"


def test_execs_per_sec_avg():
    stats = AFLplusplusFuzzStats(
        num_instances=2, execs=2000, crashes=0, hangs=0, execs_per_sec_sum=200.0
    )
    assert stats.execs_per_sec_avg == 100.0


def test_empty_stats():
    stats = AFLplusplusFuzzStats()

    assert stats.num_instances == 0
    assert stats.execs == 0
    assert stats.crashes == 0
    assert stats.hangs == 0
    assert stats.execs_per_sec_sum == 0.0
    assert stats.execs_per_sec_avg == 0.0


def test_zero_division():
    stats = AFLplusplusFuzzStats(execs_per_sec_sum=1000.0, num_instances=0)
    assert stats.execs_per_sec_avg == 1000.0  # should just return sum


def test_stats_sum():
    totals = AFLplusplusFuzzStats()

    fuzzer1 = AFLplusplusFuzzStats(
        num_instances=2, execs=2000, crashes=0, hangs=0, execs_per_sec_sum=200.0
    )
    fuzzer2 = AFLplusplusFuzzStats(
        num_instances=3, execs=3000, crashes=2, hangs=5, execs_per_sec_sum=300.0
    )

    totals.add_stats_from(fuzzer1, fuzzer2)

    assert totals.num_instances == 5
    assert totals.execs == 5000
    assert totals.crashes == 2
    assert totals.hangs == 5
    assert totals.execs_per_sec_sum == 500.0
    assert totals.execs_per_sec_avg == 100.0


def test_libfuzzer_last_line_best(mocker):
    log_contents = """INFO: Running with entropic power schedule (0xFF, 100).
INFO: Seed: 3290221889
INFO: Loaded 1 modules   (94319 inline 8-bit counters): 94319 [0x1566fb0, 0x157e01f), 
INFO: Loaded 1 PC tables (94319 PCs): 94319 [0x157e020,0x16ee710), 
INFO: -fork=5: fuzzing in separate process(s)
INFO: -fork=5: 115 seed inputs, starting to fuzz in /tmp/libFuzzerTemp.FuzzWithFork246.dir
#5688: cov: 8889 ft: 8889 corp: 115 exec/s 2844 oom/timeout/crash: 0/0/0 time: 4s job: 1 dft_time: 0
  NEW_FUNC: 0x627ed0 in AlertDebugLogRegister /suricata/src/alert-debuglog.c:485
  NEW_FUNC: 0xc04ee0 in htp_list_array_create /suricata/libhtp/htp/htp_list.c:61
  NEW_FUNC: 0xc05910 in htp_list_array_push /suricata/libhtp/htp/htp_list.c:130
#15121: cov: 10893 ft: 8938 corp: 123 exec/s 3144 oom/timeout/crash: 0/0/0 time: 5s job: 2 dft_time: 0
  NEW_FUNC: 0x7360d0 in DecodePPP /suricata/src/decode-ppp.c:45
#28841: cov: 10898 ft: 8959 corp: 131 exec/s 3430 oom/timeout/crash: 0/0/0 time: 6s job: 3 dft_time: 0
#122548: cov: 10898 ft: 8995 corp: 152 exec/s 3634 oom/timeout/crash: 0/0/0 time: 13s job: 7 dft_time: 0
  NEW_FUNC: 0x728400 in DecodeIPV4 /suricata/src/decode-ipv4.c:519
#154867: cov: 10901 ft: 9003 corp: 159 exec/s 3591 oom/timeout/crash: 0/0/0 time: 15s job: 8 dft_time: 0
#191036: cov: 10901 ft: 9011 corp: 165 exec/s 3616 oom/timeout/crash: 0/0/0 time: 17s job: 9 dft_time: 0
#230172: cov: 10902 ft: 9020 corp: 171 exec/s 3557 oom/timeout/crash: 0/0/0 time: 19s job: 10 dft_time: 0
  NEW_FUNC: 0x717f60 in DecodeCHDLC /suricata/src/decode-chdlc.c:43
  NEW_FUNC: 0x739d00 in DecodeSll /suricata/src/decode-sll.c:41
#272623: cov: 10910 ft: 9047 corp: 180 exec/s 3537 oom/timeout/crash: 0/0/0 time: 24s job: 11 dft_time: 0
#664463: cov: 10939 ft: 9211 corp: 224 exec/s 3461 oom/timeout/crash: 0/0/2 time: 50s job: 18 dft_time: 0
  NEW_FUNC: 0x7353d0 in DecodeIPv4inIPv6 /suricata/src/decode-ipv6.c:52
  NEW_FUNC: 0xb4fe60 in hashword /suricata/src/util-hash-lookup3.c:178
#733834: cov: 10966 ft: 9331 corp: 246 exec/s 3468 oom/timeout/crash: 0/0/2 time: 54s job: 19 dft_time: 0
#806340: cov: 10966 ft: 9343 corp: 254 exec/s 3452 oom/timeout/crash: 0/1/2 time: 58s job: 20 dft_time: 0
"""
    stats = LibFuzzerFuzzStats()

    mocker.patch(
        "bugbane.modules.stats.fuzz.libfuzzer.open", return_value=StringIO(log_contents)
    )
    mocker.patch(
        "bugbane.modules.stats.fuzz.libfuzzer.os.path.getmtime", return_value=100.1
    )

    res = stats.read_one("hopefully/mocked/file/path")

    print(res)

    assert res is not None

    assert res["num_forks"] == 5  # from the beginning of the log

    # stats from the very last line of the log:
    assert res["execs"] == 806340
    assert res["execs_per_sec"] == 3452
    assert res["timeouts"] == 1
    assert res["crashes"] == 2

    # time stats:
    assert res["last_path"] == 100  # int of mocked return value of getmtime
    assert res["start_time"] == 100 - 58  # 58 is last recorded "time" in log


def test_libfuzzer_last_early_best(mocker):
    """
    No new corpus has been discovered for some time
    """
    log_contents = """INFO: Running with entropic power schedule (0xFF, 100).
INFO: Seed: 3290221889
INFO: Loaded 1 modules   (94319 inline 8-bit counters): 94319 [0x1566fb0, 0x157e01f), 
INFO: Loaded 1 PC tables (94319 PCs): 94319 [0x157e020,0x16ee710), 
INFO: -fork=5: fuzzing in separate process(s)
INFO: -fork=5: 115 seed inputs, starting to fuzz in /tmp/libFuzzerTemp.FuzzWithFork246.dir
#5688: cov: 8889 ft: 8889 corp: 115 exec/s 2844 oom/timeout/crash: 0/0/0 time: 4s job: 1 dft_time: 0
  NEW_FUNC: 0x627ed0 in AlertDebugLogRegister /suricata/src/alert-debuglog.c:485
  NEW_FUNC: 0xc04ee0 in htp_list_array_create /suricata/libhtp/htp/htp_list.c:61
  NEW_FUNC: 0xc05910 in htp_list_array_push /suricata/libhtp/htp/htp_list.c:130
#15121: cov: 10893 ft: 8938 corp: 123 exec/s 3144 oom/timeout/crash: 0/0/0 time: 5s job: 2 dft_time: 0
  NEW_FUNC: 0x7360d0 in DecodePPP /suricata/src/decode-ppp.c:45
#28841: cov: 10898 ft: 8959 corp: 131 exec/s 3430 oom/timeout/crash: 0/0/0 time: 6s job: 3 dft_time: 0
#122548: cov: 10898 ft: 8995 corp: 152 exec/s 3634 oom/timeout/crash: 0/0/0 time: 13s job: 7 dft_time: 0
  NEW_FUNC: 0x728400 in DecodeIPV4 /suricata/src/decode-ipv4.c:519
#154867: cov: 10901 ft: 9003 corp: 159 exec/s 3591 oom/timeout/crash: 0/1/2 time: 15s job: 8 dft_time: 0
#191036: cov: 10901 ft: 9003 corp: 159 exec/s 3616 oom/timeout/crash: 0/1/2 time: 17s job: 9 dft_time: 0
#230172: cov: 10901 ft: 9003 corp: 159 exec/s 3557 oom/timeout/crash: 0/1/2 time: 19s job: 10 dft_time: 0
#272623: cov: 10901 ft: 9003 corp: 159 exec/s 3537 oom/timeout/crash: 0/1/2 time: 24s job: 11 dft_time: 0
#664463: cov: 10901 ft: 9003 corp: 159 exec/s 3461 oom/timeout/crash: 0/1/2 time: 35s job: 18 dft_time: 0
#733834: cov: 10901 ft: 9003 corp: 159 exec/s 3468 oom/timeout/crash: 0/1/2 time: 40s job: 19 dft_time: 0
#806340: cov: 10901 ft: 9003 corp: 159 exec/s 3452 oom/timeout/crash: 0/1/2 time: 50s job: 20 dft_time: 0
"""
    stats = LibFuzzerFuzzStats()

    mocker.patch(
        "bugbane.modules.stats.fuzz.libfuzzer.open", return_value=StringIO(log_contents)
    )
    mocker.patch(
        "bugbane.modules.stats.fuzz.libfuzzer.os.path.getmtime", return_value=100.1
    )

    res = stats.read_one("hopefully/mocked/file/path")

    print(res)

    assert res is not None

    assert res["num_forks"] == 5  # from the beginning of the log

    # stats from the very last line of the log:
    assert res["execs"] == 806340
    assert res["execs_per_sec"] == 3452
    assert res["timeouts"] == 1
    assert res["crashes"] == 2

    # time stats:
    # 100 is log file modification time
    # 50 is the last recorded time
    # 15 is seconds from start to finding the last new sample
    assert res["last_path"] == 100 - 50 + 15
    assert res["start_time"] == 100 - 50


@pytest.mark.parametrize("fuzzer_type", FuzzStatsFactory.registry)
def test_fuzzer_type_consistent(fuzzer_type: str):
    """
    FuzzStats return fuzzer_type by which they are registered in FuzzStatsFactory
    """
    fuzz_stats: FuzzStats = FuzzStatsFactory.create(fuzzer_type)
    assert fuzzer_type == fuzz_stats.fuzzer_type()


def test_gofuzz(mocker: MockerFixture):
    log_contents = b"""2022/01/11 11:08:34 workers: 6, corpus: 731 (25m57s ago), crashers: 0, restarts: 1/9996, execs: 147991207 (19024/sec), cover: 825, uptime: 2h9m                                      
2022/01/11 11:08:37 workers: 6, corpus: 731 (26m0s ago), crashers: 0, restarts: 1/9996, execs: 148051622 (19025/sec), cover: 825, uptime: 2h9m                                       
2022/01/11 11:08:40 workers: 6, corpus: 731 (26m3s ago), crashers: 0, restarts: 1/9996, execs: 148109989 (19025/sec), cover: 825, uptime: 2h9m                                       
2022/01/11 11:08:43 workers: 6, corpus: 731 (26m6s ago), crashers: 0, restarts: 1/9996, execs: 148167957 (19025/sec), cover: 825, uptime: 2h9m                                       
2022/01/11 11:08:46 workers: 6, corpus: 731 (26m9s ago), crashers: 0, restarts: 1/9996, execs: 148227700 (19025/sec), cover: 825, uptime: 2h9m                                       
2022/01/11 11:08:49 workers: 6, corpus: 731 (26m12s ago), crashers: 0, restarts: 1/9996, execs: 148284459 (19025/sec), cover: 825, uptime: 2h9m                                      
2022/01/11 11:08:52 workers: 6, corpus: 731 (26m15s ago), crashers: 0, restarts: 1/9996, execs: 148340958 (19025/sec), cover: 825, uptime: 2h9m                                      
2022/01/11 11:08:55 workers: 6, corpus: 731 (26m18s ago), crashers: 0, restarts: 1/9996, execs: 148398992 (19025/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:08:58 workers: 6, corpus: 731 (26m21s ago), crashers: 0, restarts: 1/9997, execs: 148459864 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:01 workers: 6, corpus: 731 (26m24s ago), crashers: 0, restarts: 1/9997, execs: 148518216 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:04 workers: 6, corpus: 731 (26m27s ago), crashers: 0, restarts: 1/9997, execs: 148570422 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:07 workers: 6, corpus: 731 (26m30s ago), crashers: 0, restarts: 1/9996, execs: 148622324 (19025/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:10 workers: 6, corpus: 731 (26m33s ago), crashers: 0, restarts: 1/9996, execs: 148682219 (19025/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:13 workers: 6, corpus: 731 (26m36s ago), crashers: 0, restarts: 1/9996, execs: 148743039 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:16 workers: 6, corpus: 731 (26m39s ago), crashers: 0, restarts: 1/9996, execs: 148800164 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:19 workers: 6, corpus: 731 (26m42s ago), crashers: 0, restarts: 1/9996, execs: 148862010 (19026/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:22 workers: 6, corpus: 731 (26m45s ago), crashers: 0, restarts: 1/9996, execs: 148922520 (19027/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:25 workers: 6, corpus: 731 (26m48s ago), crashers: 0, restarts: 1/9996, execs: 148981912 (19027/sec), cover: 825, uptime: 2h10m                                     
2022/01/11 11:09:28 workers: 6, corpus: 731 (26m51s ago), crashers: 13, restarts: 1/9996, execs: 149042657 (19028/sec), cover: 825, uptime: 2h10m
2022/01/12 09:02:01 shutting down..."""
    stats = GoFuzzFuzzStats()

    mocker.patch(MOCK_FILE_UTILS_OPEN, return_value=BytesIO(log_contents))
    mocker.patch(MOCK_FILE_UTILS_OS_PATH_GETSIZE, return_value=3421)
    mocker.patch(
        "bugbane.modules.stats.fuzz.gofuzz.time.time", return_value=3 * 60 * 60
    )

    res = stats.read_one("hopefully/mocked/file/path")

    print(res)

    assert res is not None

    assert res["num_workers"] == 6

    # stats from the very last line of the log:
    assert res["execs"] == 149042657
    assert res["execs_per_sec"] == 19028
    assert res["timeouts"] == 0
    assert res["crashes"] == 13

    # time stats:
    # now (3h) - duration (2h10m) = 50m
    assert res["start_time"] == 50 * 60

    # now (3h) - last_path_delta (26m51s) = 2h33m9s
    assert res["last_path"] == 2 * 3600 + 33 * 60 + 9


def test_gotest(mocker: MockerFixture):
    """
    Test parsing of `go test` fuzzing statistics.
    NOTE: native fuzzing is available in Go since go1.18.
    """

    log_contents = """fuzz: elapsed: 0s, gathering baseline coverage: 0/7 completed
fuzz: elapsed: 0s, gathering baseline coverage: 7/7 completed, now fuzzing with 5 workers
fuzz: elapsed: 3s, execs: 438524 (146164/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 6s, execs: 931701 (164127/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 9s, execs: 1423838 (164287/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 12s, execs: 1916848 (164097/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 15s, execs: 2431438 (171526/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 18s, execs: 2912488 (160592/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 21s, execs: 3399798 (162428/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 24s, execs: 3896759 (164879/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 27s, execs: 4373523 (159709/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 30s, execs: 4844644 (156779/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 33s, execs: 5328713 (161575/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 36s, execs: 5845473 (172254/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 39s, execs: 6299640 (151408/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 42s, execs: 6767188 (155850/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 45s, execs: 7245679 (159524/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 48s, execs: 7717725 (157320/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 51s, execs: 8197280 (159616/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 54s, execs: 8671769 (158400/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 57s, execs: 9139587 (155943/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m0s, execs: 9610020 (156821/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m3s, execs: 10069317 (153092/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m6s, execs: 10582206 (170939/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m9s, execs: 11077164 (164995/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m12s, execs: 11556946 (159927/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m15s, execs: 12034289 (159116/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m18s, execs: 12512924 (159543/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m21s, execs: 12990618 (159265/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m24s, execs: 13491021 (166523/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m27s, execs: 14006344 (172065/sec), new interesting: 0 (total: 7)
fuzz: elapsed: 1m30s, execs: 14498556 (163794/sec), new interesting: 0 (total: 7)"""

    stats = GoTestFuzzStats()

    mocker.patch(
        "bugbane.modules.stats.fuzz.gotest.open", return_value=StringIO(log_contents)
    )
    mocker.patch(
        "bugbane.modules.stats.fuzz.gotest.os.path.getmtime", return_value=100.1
    )

    res = stats.read_one("hopefully/mocked/file/path")

    print(res)

    assert res is not None

    assert res["num_workers"] == 5

    # stats from the very last line of the log:
    assert res["execs"] == 14498556
    assert res["execs_per_sec"] == 163794
    assert res["timeouts"] == 0
    assert res["crashes"] == 0

    # time stats:
    # last modification time (100s) - duration (1m30s=90s) = 10s
    assert res["start_time"] == 10

    # last modification time (100s) - duration (90s) + last_path_delta (3s) = 13s
    assert res["last_path"] == 13


def test_gotest_crash(mocker: MockerFixture):
    """
    `go test` fuzzing statistics with some crash detected.
    """

    log_contents = """fuzz: elapsed: 0s, gathering baseline coverage: 0/1 completed
fuzz: elapsed: 0s, gathering baseline coverage: 1/1 completed, now fuzzing with 1 workers
fuzz: elapsed: 3s, execs: 50820 (16937/sec), new interesting: 3 (total: 4)
fuzz: elapsed: 6s, execs: 103222 (17465/sec), new interesting: 3 (total: 4)
fuzz: minimizing 47-byte failing input file
fuzz: elapsed: 8s, minimizing
--- FAIL: FuzzParse (7.98s)
    --- FAIL: FuzzParse (0.00s)
        testing.go:1356: panic: test
            goroutine 138628 [running]:
            runtime/debug.Stack()
                /usr/lib/go/src/runtime/debug/stack.go:24 +0xdb
            testing.tRunner.func1()
                /usr/lib/go/src/testing/testing.go:1356 +0x1f2
            panic({0x5d0540, 0x63de48})
                /usr/lib/go/src/runtime/panic.go:884 +0x212
            _/src/go.SimpleParse(...)
                /src/go/fuzz_test.go:14
            _/src/go.FuzzParse.func1(0x0?, {0xc006deb248, 0x5, 0x4663f9?})
                /src/go/fuzz_test.go:20 +0x3eb
            reflect.Value.call({0x5d20e0?, 0x60e800?, 0x13?}, {0x5fff7a, 0x4}, {0xc006e26b70, 0x2, 0x2?})
                /usr/lib/go/src/reflect/value.go:584 +0x8c5
            reflect.Value.Call({0x5d20e0?, 0x60e800?, 0x51b?}, {0xc006e26b70?, 0x6ffc68?, 0x71f580?})
                /usr/lib/go/src/reflect/value.go:368 +0xbc
            testing.(*F).Fuzz.func1.1(0x0?)
                /usr/lib/go/src/testing/fuzz.go:337 +0x231
            testing.tRunner(0xc006e36b60, 0xc006e32480)
                /usr/lib/go/src/testing/testing.go:1446 +0x10b
            created by testing.(*F).Fuzz.func1
                /usr/lib/go/src/testing/fuzz.go:324 +0x5b9


    Failing input written to testdata/fuzz/FuzzParse/3e4c6ce8bf00c2198ddd89dbd9debfda7684b131ab38b2338d4ca4c773a47cb6
    To re-run:
    go test -run=FuzzParse/3e4c6ce8bf00c2198ddd89dbd9debfda7684b131ab38b2338d4ca4c773a47cb6
FAIL
coverage: 0.0% of statements"""

    stats = GoTestFuzzStats()

    mocker.patch(
        "bugbane.modules.stats.fuzz.gotest.open", return_value=StringIO(log_contents)
    )
    mocker.patch(
        "bugbane.modules.stats.fuzz.gotest.os.path.getmtime", return_value=100.1
    )

    res = stats.read_one("hopefully/mocked/file/path")

    print(res)

    assert res is not None

    assert res["num_workers"] == 1

    # stats from the very last line of the log:
    assert res["execs"] == 103222
    assert res["execs_per_sec"] == 17465
    assert res["timeouts"] == 0
    assert res["crashes"] == 1

    # time stats:
    # last modification time (100s) - duration (6s) = 94s
    assert res["start_time"] == 94

    # last modification time (100s) - duration (6s) + last_path_delta (3s) = 97s
    assert res["last_path"] == 97
