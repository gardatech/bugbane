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

from io import BytesIO, StringIO
from pytest_mock import MockerFixture

from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats
from bugbane.modules.stats.fuzz.aflplusplus import AFLplusplusFuzzStats
from bugbane.modules.stats.fuzz.libfuzzer import LibFuzzerFuzzStats
from bugbane.modules.stats.fuzz.gofuzz import GoFuzzFuzzStats
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

    assert res["num_forks"] == 5  # from the beginning of the log

    # stats from the very last line of the log:
    assert res["execs"] == 806340
    assert res["execs_per_sec"] == 3452
    assert res["timeouts"] == 1
    assert res["crashes"] == 2

    # time stats:
    assert res["last_path"] == 100  # int of mocked return value of getmtime
    assert res["start_time"] == 100 - 50  # 50 is last recorded "time" in log


def test_fuzzer_type_consistent():
    """
    FuzzStats return fuzzer_type by which they are registered in FuzzStatsFactory
    """
    for fuzzer_type in FuzzStatsFactory.registry:
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
