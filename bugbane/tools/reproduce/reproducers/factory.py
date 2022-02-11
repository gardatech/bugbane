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

from typing import Dict, Callable, Optional

import logging

log = logging.getLogger(__name__)

from bugbane.modules.factory import Factory

from .reproducer import Reproducer


class ReproducerFactory(Factory):
    """Factory for Reproducer subclasses"""

    registry: Dict[str, Reproducer] = {}
    default: Optional[Reproducer] = None

    @classmethod
    def register_default(cls) -> Callable:
        """Register default class in internal registry"""

        def wrapper(wrapped: Callable) -> Callable:
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
