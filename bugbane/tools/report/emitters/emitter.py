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

from abc import ABC, abstractmethod
from typing import Optional, Union

from bugbane.modules.fuzz_data_suite import FuzzDataSuite


class EmitterError(Exception):
    """Exception class for errors in Emitter class"""


class TemplateRenderError(EmitterError):
    """Exception class for errors during process of rendering template"""


class Emitter(ABC):
    def __init__(self):
        self.suite: Optional[FuzzDataSuite] = None

    def assign_suite(self, suite: FuzzDataSuite):
        """
        Assigns FuzzDataSuita instance to this instance of FuzzReportEmitter
        """
        self.suite = suite

    def set_template_path(self, template_dir: str, template_name: str):
        """
        Sets path to templates
        """
        self.template_dir = template_dir
        self.template_name = template_name

    @abstractmethod
    def get_format_name(self) -> str:
        """
        Returns name of the format, e.g. "Markdown" or "Unix Makefiles"
        """

    @abstractmethod
    def get_report_file_extension(self) -> str:
        """
        Return extension for file of generated format, e.g. "md".
        Should return '' or None if there should be no file extension
        """

    @abstractmethod
    def render(self) -> Union[str, bytes]:
        """
        Renders data from FuzzDataSuite to bytes or str.
        Fields with None value should't be in result (whole section for this field should be missing).
        Raise TemplateRenderError in case of missing crucial data
        """

    @abstractmethod
    def save_bundle_files(self, path: str):
        """
        Creates additional files that should be bundled with report,
        puts them to path
        """
