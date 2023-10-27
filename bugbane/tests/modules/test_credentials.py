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

from typing import Optional

import pytest

from bugbane.modules.credentials import (
    Credentials,
    EmptyLoginException,
    NoSecretDefinedException,
    InvalidCredentialsNameException,
    make_env_var_name,
)


def test_init() -> None:
    c = Credentials(login="user", secret="1234")
    assert c.login == "user"
    assert c.secret == "1234"


def test_init_missing_login_is_ok() -> None:
    c = Credentials(secret="1234")
    assert c.login is None
    assert c.secret == "1234"


@pytest.mark.parametrize(
    "login",
    [
        None,
        "user",
    ],
)
def test_init_empty_secret_is_ok(login: Optional[str]) -> None:
    c = Credentials(login=login, secret="")
    assert c.secret == ""


def test_init_empty_login_raises() -> None:
    with pytest.raises(EmptyLoginException):
        Credentials(login="", secret="1234")


@pytest.mark.parametrize(
    "cred_name, var_name",
    [
        ("a", "A"),
        ("1", "1"),
        ("Abc123", "ABC123"),
        ("A!@#B$%^C", "A_B_C"),
        ("defect-dojo", "DEFECT_DOJO"),
        ("defect_dojo", "DEFECT_DOJO"),
    ],
)
def test_make_env_var_name(cred_name: str, var_name: str) -> None:
    assert make_env_var_name(cred_name) == var_name


@pytest.mark.parametrize(
    "invalid_cred_name",
    [
        "",
        "-",
        "_",
        "___",
        "##$%^&",
    ],
)
def test_make_env_var_name_bad(invalid_cred_name: str) -> None:
    with pytest.raises(InvalidCredentialsNameException, match="invalid credentials name"):
        make_env_var_name(invalid_cred_name)


def test_make_credentials_from_env() -> None:
    fake_env = {
        "LANG": "C",
        "BB_DEFECT_DOJO_SECRET": "d0jo_s3cret",
        "PATH": "/usr/bin:/usr/local/bin:/bin",
        "BB_DEFECT_DOJO_LOGIN": "dojouser",
    }
    c = Credentials.from_env(credentials_name="defect-dojo", env=fake_env)
    assert c.login == "dojouser"
    assert c.secret == "d0jo_s3cret"

@pytest.mark.parametrize(
    "login",
    [
        None,
        "user",
    ]
)
def test_make_credentials_from_env_empty_secret_is_ok(login: str) -> None:
    fake_env = {
        "LANG": "C",
        "BB_SOME_SECRET": "",
        "PATH": "/usr/bin:/usr/local/bin:/bin",
        "BB_SOME_LOGIN": login,
    }
    c = Credentials.from_env(credentials_name="some", env=fake_env)
    assert c.login == login
    assert c.secret == ""

def test_make_credentials_from_env_only_secret() -> None:
    fake_env = {
        "LANG": "C",
        "BB_SOME_SECRET": "s3cret",
        "PATH": "/usr/bin:/usr/local/bin:/bin",
    }
    c = Credentials.from_env(credentials_name="some", env=fake_env)
    assert c.login is None
    assert c.secret == "s3cret"


def test_make_credentials_from_env_only_login_is_bad() -> None:
    fake_env = {
        "LANG": "C",
        "BB_SOME_LOGIN": "user",
        "PATH": "/usr/bin:/usr/local/bin:/bin",
    }
    with pytest.raises(NoSecretDefinedException, match="no secret was defined"):
        Credentials.from_env(credentials_name="some", env=fake_env)
