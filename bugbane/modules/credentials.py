# Copyright 2022-2024 Garda Technologies, LLC. All rights reserved.
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

"""
Module defining Credentials class and its exceptions.
"""

from typing import Optional, MutableMapping, TypeVar, Type
from dataclasses import dataclass

import os
import re


class CredentialsException(Exception):
    """Exception class for Credentials class."""


class EmptyLoginException(CredentialsException):
    """Exception: login was defined with an empty value."""


class NoSecretDefinedException(CredentialsException):
    """Exception: secret wasn't defined."""


class InvalidCredentialsNameException(CredentialsException):
    """Exception: credentials name was invalid."""


_T = TypeVar("_T")


@dataclass
class Credentials:
    """
    Class for storing credentials: optional login + secret.
    """

    secret: str
    login: Optional[str] = None

    def __post_init__(self) -> None:
        """Raise if login defined, but empty."""
        if self.login is None:
            return

        if len(self.login) < 1:
            raise EmptyLoginException("empty login was defined")

    @classmethod
    def from_env(
        cls: Type[_T],
        credentials_name: str,
        env: Optional[MutableMapping[str, str]] = None,
    ) -> _T:
        """
        Get credentials from env.
        If no `env` is passed, `os.environ` is used.
        """

        cred_prefix = "BB_"
        login_suffix = "_LOGIN"
        secret_suffix = "_SECRET"
        re_many_unders = re.compile(r"_{2,}")

        login_var_name = make_env_var_name(credentials_name)
        env_login = cred_prefix + login_var_name + login_suffix
        env_login = re_many_unders.sub(string=env_login, repl="_")

        secret_var_name = make_env_var_name(credentials_name)
        env_secret = cred_prefix + secret_var_name + secret_suffix
        env_secret = re_many_unders.sub(string=env_secret, repl="_")

        env = env or os.environ

        try:
            return cls(login=env.get(env_login), secret=env[env_secret])
        except KeyError as e:
            raise NoSecretDefinedException("no secret was defined") from e


def make_env_var_name(input_name: str) -> str:
    re_invalid_chars = re.compile(r"[^a-zA-Z0-9_]+")
    valid_name = re_invalid_chars.sub(string=input_name, repl="_")
    if len(valid_name) == 0 or set(valid_name) == {"_"}:
        raise InvalidCredentialsNameException(
            "invalid credentials name. Please only use letters from this range: _, a-z, A-Z, 0-9"
        )
    return valid_name.upper()
