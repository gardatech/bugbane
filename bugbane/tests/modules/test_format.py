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

import pytest

from bugbane.modules import format


def test_squeeze_spaces():
    text = "    Hello,      world! Test  spaces here    "

    assert format.squeeze_spaces(text) == " Hello, world! Test spaces here "


def test_squeeze_spaces_ok_string():
    text = "Hello, world! Test spaces here"

    assert format.squeeze_spaces(text) == "Hello, world! Test spaces here"


def test_squeeze_spaces_tabs():
    text = " \t\tHello,    \t  world!\tTest  spaces here\t    "

    assert format.squeeze_spaces(text) == " Hello, world!\tTest spaces here "


def test_metric_try_to_float():
    in_out = [
        ("127", 127.0),
        ("0.5", 0.5),
        ("-99.4", -99.4),
        ("51%", 51.0),
        ("66.6%", 66.6),
        ("1000000000", 1000000000.0),
    ]

    for inp, exp in in_out:
        assert format.metric_try_to_float(inp) == exp


def test_remove_trailing_zeroes():
    in_out = [
        (0.0, "0"),
        (11, "11"),
        (-199.5, "-199.5"),
        (1000.005, "1000.005"),
        (1.10, "1.1"),
        (-1000000.0, "-1000000"),
    ]

    for inp, exp in in_out:
        assert format.remove_float_trailing_zeroes(inp) == exp


def test_zfill_to_collection_size():
    in_out = [
        ((1, 10), "01"),
        ((55, 55), "55"),
        ((55, 56), "55"),
        ((1, 100), "001"),
        ((99, 99), "99"),
        ((99, 100), "099"),
        ((1000, 100), "1000"),
    ]

    for inp, exp in in_out:
        assert format.zfill_to_collection_size(*inp) == exp


def test_count_to_report_count():
    in_out = [
        (0, "0"),
        (7.0, "7"),
        (-129.5600, "-129.56"),
        (999.6, "999.6"),
        (1000.27, "1K"),
        (1028, "1K"),
        (2427.58, "2.4K"),
        (9999.99, "10K"),
        (3_700_000, "3.7M"),
        (999_792_500, "999.79M"),
        (9_000_001_234, "9B"),
        (9_001_001_234, "9.001B"),
        (9_702_500_000, "9.7025B"),
    ]

    for inp, exp in in_out:
        assert format.count_to_report_count(inp) == exp


def test_count_to_report_count_cyr():
    in_out = [
        (0, "0"),
        (7.0, "7"),
        (-129.5600, "-129.56"),
        (999.6, "999.6"),
        (1000.27, "1 тыс"),
        (1028, "1 тыс"),
        (2427.58, "2.4 тыс"),
        (9999.99, "10 тыс"),
        (3_700_000, "3.7 млн"),
        (999_792_500, "999.79 млн"),
        (9_000_001_234, "9 млрд"),
        (9_001_001_234, "9.001 млрд"),
        (9_702_500_000, "9.7025 млрд"),
    ]

    for inp, exp in in_out:
        assert format.count_to_report_count_cyr(inp) == exp


def test_cyr_word_for_quantity():
    # продолжительность составила ...
    in_out = [
        ((0, "days"), "дней"),
        ((1, "days"), "день"),
        ((2, "days"), "дня"),
        ((3, "hours"), "часа"),
        ((4, "hours"), "часа"),
        ((5, "hours"), "часов"),
        ((171, "hours"), "час"),
        ((6, "minutes"), "минут"),
        ((10, "minutes"), "минут"),
        ((11, "minutes"), "минут"),
        ((12, "minutes"), "минут"),
        ((13, "minutes"), "минут"),
        ((14, "minutes"), "минут"),
        ((15, "minutes"), "минут"),
        ((51, "minutes"), "минуту"),
        ((123, "minutes"), "минуты"),
        ((20, "seconds"), "секунд"),
        ((21, "seconds"), "секунду"),
        ((32, "seconds"), "секунды"),
        ((43, "seconds"), "секунды"),
        ((154, "seconds"), "секунды"),
        ((361, "seconds"), "секунду"),
        ((411, "seconds"), "секунд"),
        ((1111, "seconds"), "секунд"),
        ((1001, "seconds"), "секунду"),
    ]

    for inp, exp in in_out:
        assert format.cyr_word_for_quantity(*inp) == exp


def test_cyr_word_for_time_unit_bad():
    with pytest.raises(ValueError):
        format.cyr_word_for_quantity(127, "!!! millions of years !!!")


def test_seconds_to_dhms():
    in_out = [
        (0, (0, 0, 0, 0)),
        (1, (0, 0, 0, 1)),
        (59, (0, 0, 0, 59)),
        (60, (0, 0, 1, 0)),
        (65, (0, 0, 1, 5)),
        (3599, (0, 0, 59, 59)),
        (3600, (0, 1, 0, 0)),
        (3666, (0, 1, 1, 6)),
        (86399, (0, 23, 59, 59)),
        (86400, (1, 0, 0, 0)),
        (86496, (1, 0, 1, 36)),
        (259200, (3, 0, 0, 0)),
        (8553600, (99, 0, 0, 0)),
        (43200000, (500, 0, 0, 0)),
    ]
    for inp, exp in in_out:
        assert format.seconds_to_dhms(inp) == exp


def test_golang_duration_to_seconds():
    in_out = [
        ("", 0),
        ("0s", 0),
        ("1s", 1),
        ("59s", 59),
        ("1m0s", 60),
        ("1m5s", 65),
        ("59m59s", 3599),
        ("1h0m0s", 3600),
        ("1h1m6s", 3666),
        ("23h59m59s", 86399),
        ("24h0m0s", 86400),
        ("24h1m36s", 86496),
        ("72h0m0s", 259200),
        ("2376h0m0s", 8553600),
        ("12000h0m0s", 43200000),
        ("2h10m", 7800),
    ]
    for inp, exp in in_out:
        assert format.golang_duration_to_seconds(inp) == exp


def test_seconds_to_report_duration_cyr():
    # продолжительность составила ...
    in_out = [
        (0, "0 секунд"),
        (1, "1 секунду"),
        (59, "59 секунд"),
        (60, "1 минуту"),
        (65, "1 минуту 5 секунд"),
        (3599, "59 минут 59 секунд"),
        (3600, "1 час"),
        (3666, "1 час 1 минуту"),
        (86399, "23 часа 59 минут"),
        (86400, "1 день"),
        (86496, "1 день"),
        (259200, "3 дня"),
        (8553600, "99 дней"),
        (43200000, "500 дней"),
    ]
    for inp, exp in in_out:
        assert format.seconds_to_report_duration_cyr(inp) == exp


def test_count_to_report_count_with_unit_cyr():
    in_out = [
        ((0, "crashes"), "0 падений"),
        ((11, "crashes"), "11 падений"),
        ((21, "crashes"), "21 падение"),
        ((221, "hangs"), "221 зависание"),
        ((100_001, "crashes"), "100 тыс. падений"),
        ((100_101, "crashes"), "100.1 тыс. падений"),
        ((2_023_400, "hangs"), "2.02 млн. зависаний"),
        ((2_023_400_000, "hangs"), "2.0234 млрд. зависаний"),
    ]
    for inp, exp in in_out:
        assert format.count_to_report_count_with_unit_cyr(*inp) == exp


def test_seconds_to_hms():
    in_out = [
        (0, "00:00:00"),
        (59, "00:00:59"),
        (60, "00:01:00"),
        (61, "00:01:01"),
        (82919, "23:01:59"),
        (1072743, "297:59:03"),
    ]
    for inp, exp in in_out:
        assert format.seconds_to_hms(inp) == exp
