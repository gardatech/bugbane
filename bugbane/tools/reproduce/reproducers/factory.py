# Copyright 2022-2025 Garda Technologies, LLC. All rights reserved.
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

from typing import Dict, Callable, Optional, Type
from copy import deepcopy

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.factory import Factory

from .reproducer import Reproducer


class ReproducerFactory(Factory[Reproducer]):
    """Factory/Registry for Reproducer subclasses"""

    registry: Dict[str, Type[Reproducer]] = {}
    default: Optional[Type[Reproducer]] = None

    @classmethod
    def register_default(cls) -> Callable[[Type[Reproducer]], Type[Reproducer]]:
        """Register default class in internal registry"""

        def wrapper(wrapped: Type[Reproducer]) -> Type[Reproducer]:
            if cls.default is not None:
                log.warning("replacing default class in %s", cls.__name__)
            cls.default = wrapped
            return wrapped

        return wrapper

    @classmethod
    def create(cls, wanted_class: str) -> Reproducer:
        """Create concrete class. If not found, return cls.default()"""
        ret = cls.registry.get(wanted_class) or cls.default

        if ret is None:
            raise TypeError(
                f"class {wanted_class} is not registered in factory {cls.__name__}"
            )

        return ret()

    @classmethod
    def create_from_reproduce_cmd(cls, reproduce_cmd: str) -> Reproducer:
        """
        Return a new instance of Reproducer subclass matching to `reproduce_cmd`.
        """
        name = cls.get_reproducer_name_from_reproduce_cmd(reproduce_cmd)
        return cls.create(name)

    @classmethod
    def get_reproducer_name_from_reproduce_cmd(cls, reproduce_cmd: str) -> str:
        """
        Return name by which Reproducer subclass matching to `reproduce_cmd` was registered.
        The name can then be used to get a new Reproducer subclass instance.

        This method can be used for caching reproducer instances
        """

        reproducers = deepcopy(cls.registry)
        if cls.default is not None:
            reproducers["~~~DEFAULT~~~"] = cls.default

        for name, reproducer in reproducers.items():
            for m in reproducer.reproduce_cmd_matchers():
                if m in reproduce_cmd:
                    return name

        raise TypeError(
            f"failed to find reproducer for reproduce command '{reproduce_cmd}'"
        )
