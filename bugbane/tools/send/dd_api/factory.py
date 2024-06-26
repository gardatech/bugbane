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
Module describes DefectDojoAPIFactory class to provide different DefectDojoAPI implementations
"""
from typing import Dict, Type

from bugbane.modules.factory import Factory

from .abc import DefectDojoAPI


class DefectDojoAPIFactory(Factory[DefectDojoAPI]):
    registry: Dict[str, Type[DefectDojoAPI]] = {}
