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

from typing import Callable
from abc import ABC

import logging

log = logging.getLogger(__name__)


class Factory(ABC):

    registry = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """Register class in internal registry"""

        def wrapper(wrapped) -> Callable:
            if name in cls.registry:
                log.warning("replacing '%s' class in %s registry", name, cls.__name__)
            cls.registry[name] = wrapped
            return wrapped

        return wrapper

    @classmethod
    def create(cls, wanted_class: str):
        """Create concrete class"""
        if wanted_class not in cls.registry:
            raise TypeError(
                f"class {wanted_class} is not registered in factory {cls.__name__}"
            )

        return cls.registry[wanted_class]()
