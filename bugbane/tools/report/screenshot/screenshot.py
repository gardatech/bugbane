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

from abc import ABC, abstractmethod


class ScreenshotError(RuntimeError):
    """Exception class for errors that happen in ScreenshotMaker subclasses."""


class ScreenshotMaker(ABC):
    """ABC for 'screenshot' generator classes."""

    @abstractmethod
    def convert(self, input_file_path: str, output_file_path: str, dpi: int):
        """
        Convert input file to screenshot, save it at output_file_path.
        In case of errors raise ScreenshotError
        """
