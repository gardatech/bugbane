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

from typing import Optional, Union

from jinja2 import Environment, FileSystemLoader
import logging

log = logging.getLogger(__name__)

from .emitter import EmitterError, TemplateRenderError
from .emitter_with_screenshots import EmitterWithScreenshots
from .factory import EmitterFactory


@EmitterFactory.register("md")
class MarkdownEmitter(EmitterWithScreenshots):
    """
    Markdown report generator.
    Uses Jinja2
    """

    def __init__(self):
        super().__init__()
        self.jinja_env: Optional[Environment] = None

    def set_template_path(self, template_dir: str, template_name: str):
        super().set_template_path(template_dir, template_name)
        self._create_jinja_env()

    def _create_jinja_env(self):
        template_loader = FileSystemLoader(self.template_dir)
        self.jinja_env = Environment(
            loader=template_loader, extensions=["jinja2.ext.loopcontrols"]
        )

    def get_format_name(self) -> str:
        return "Markdown"

    def get_report_file_extension(self) -> str:
        return "md"

    def save_bundle_files(self, path: str):
        """
        For markdown format there's nothing to be done here
        """
        pass

    def render(self) -> Union[str, bytes]:
        log.trace("rendering self.template_name=%s", self.template_name)
        template = self.jinja_env.get_template(self.template_name)
        return template.render(data=self._prepare_data_for_render())

    def _prepare_data_for_render(self) -> dict:
        data = self.suite.to_data_dict()

        if self.screehsnot_paths:
            data.update(self.screehsnot_paths)
        return data
