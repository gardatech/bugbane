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

from typing import Union, Tuple

import re


def metric_try_to_float(s: str) -> Union[float, str]:
    try:
        if "%" in s:
            s = s[:-1]
        return float(s)
    except ValueError:
        return s


def squeeze_spaces(s: str) -> str:
    return re.sub(r"\s{2,}", " ", s)


def remove_float_trailing_zeroes(x: float) -> str:
    return ("%f" % x).rstrip("0").rstrip(".")


def zfill_to_collection_size(index: int, collection_size: int) -> str:
    """
    Prepends amount of zeroes required for indexes to be string-sortable in terms of given collection size.
    Examples:
        for 10 items prepends up to 1 zero: 1 -> "01", 10 -> "10"
        for 100 items prepends up to 2 zeroes: 7 -> "007", "13" -> "013"
    """
    positions = len(str(collection_size))
    return str(index).zfill(positions)


def count_to_report_count(x: int) -> str:
    """
    Convert possibly big number to values like:
    129
    235.4K
    18.12M
    1.2215B
    """

    rules = [
        (1_000_000_000, "B", 4),
        (1_000_000, "M", 2),
        (1000, "K", 1),
    ]

    for rule in rules:
        divisor, letter, num_digits = rule
        if x >= divisor:
            s = remove_float_trailing_zeroes(round((x / divisor), num_digits))
            return f"{s}{letter}"

    return remove_float_trailing_zeroes(x)


def count_to_report_count_cyr(x: int) -> str:
    """
    Convert possibly big number to values like:
    129
    235 тыс
    18.12 млн
    1.2215 млрд
    """

    repls = {
        "K": " тыс",
        "M": " млн",
        "B": " млрд",
    }

    report_count = count_to_report_count(x)

    for k, v in repls.items():
        if k in report_count:
            return report_count.replace(k, v)

    return report_count


def count_to_report_count_with_unit_cyr(x: int, unit: str) -> str:
    """
    Convert possibly big number to values with cyrillic units in correct plural form like:
    122 падения
    235 тыс. падений
    18.12 млн. зависаний
    1.2215 млрд. падений
    """
    s = count_to_report_count_cyr(x)
    if s[-1].isdigit():
        return s + " " + cyr_word_for_quantity(x, unit)  # return form that fits

    return s + ". " + cyr_word_for_quantity(11, unit)  # return plural form


def seconds_to_dhms(x: int) -> Tuple[int, int, int, int]:
    """
    Returns days, hours, minutes, seconds converted from total seconds x.
    """

    s = x % 60
    m = (x // 60) % 60
    h = (x // 3600) % 24
    d = x // 86400
    return d, h, m, s


def golang_duration_to_seconds(d: str) -> int:
    """
    Convert values like "276h41m7s" to number of seconds
    """

    add = ""
    for c in ["s", "m", "h"]:
        if d.endswith(c):
            break
        add += "0" + c
    d += add
    hms = [int(x) for x in re.split(r"\D", d)[:-1]]
    res = hms[-1]
    if len(hms) > 1:
        res += hms[-2] * 60
        if len(hms) > 2:
            res += hms[-3] * 60 * 60
    return res


def seconds_to_report_duration_cyr(x: int) -> str:
    units = ["days", "hours", "minutes", "seconds"]
    d, h, m, s = seconds_to_dhms(x)
    zipped = zip((d, h, m, s), units)

    parts = [
        f"{quantity} {cyr_word_for_quantity(quantity, unit)}"
        for quantity, unit in zipped
    ]

    pairs = [(d, h), (h, m), (m, s)]
    for i, (big, small) in enumerate(pairs):
        if big > 0:
            if small > 0:
                return " ".join(parts[i : i + 2])
            return parts[i]

    return parts[3]


def cyr_word_for_quantity(x: int, unit: str) -> str:
    """
    Returns correct word form of specified unit for specified quantity
    """
    unit_forms = {
        # 0|5|11, 1|21, 3|24|105
        # продолжительность составила
        "days": ["дней", "день", "дня"],
        "hours": ["часов", "час", "часа"],
        "minutes": ["минут", "минуту", "минуты"],
        "seconds": ["секунд", "секунду", "секунды"],
        # тестирование выполнялось на N ядрах
        "on_cores": ["ядрах", "ядре", "ядрах"],
        # N запусков
        "execs": ["запусков", "запуск", "запуска"],
        # обнаружено N падений|зависаний
        "crashes": ["падений", "падение", "падения"],
        "hangs": ["зависаний", "зависание", "зависания"],
    }

    if unit not in unit_forms:
        raise ValueError(f"bad unit {unit}")

    words = unit_forms[unit]

    mod100 = x % 100
    if mod100 in (11, 12, 13, 14):
        return words[0]

    mod10 = x % 10
    if mod10 == 1:
        return words[1]

    if mod10 in (2, 3, 4):
        return words[2]

    return words[0]


def seconds_to_hms(seconds: int) -> str:
    """
    Returns string like "23:01:59" or "297:59:03" from seconds.
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
