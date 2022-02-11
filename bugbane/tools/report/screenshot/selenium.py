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

import os
from selenium.webdriver import Firefox, FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException

import logging

log = logging.getLogger(__name__)

from .screenshot import ScreenshotMaker, ScreenshotError
from .factory import ScreenshotMakerFactory


@ScreenshotMakerFactory.register("selenium")
class SeleniumScreenshotMaker(ScreenshotMaker):
    """Use selenium + geckodriver on input html"""

    def _create_webdriver(self) -> Firefox:
        options = FirefoxOptions()
        options.headless = True
        driver = Firefox(options=options)
        driver.set_window_size(800, 600)
        return driver

    def convert(self, input_file_path: str, output_file_path: str, dpi: int):
        input_file_url = "file://" + os.path.abspath(input_file_path)
        output_abspath = os.path.abspath(output_file_path)

        driver = None
        try:
            driver = self._create_webdriver()
            driver.get(input_file_url)
            driver.implicitly_wait(2)
            success = driver.get_screenshot_as_file(output_abspath)
        except TimeoutException as e:
            raise ScreenshotError(
                f"selenium timeout while opening {input_file_url}"
            ) from e
        except WebDriverException as e:
            raise ScreenshotError(f"selenium exception: {e}") from e
        finally:
            if driver:
                driver.quit()

        if not success:
            raise ScreenshotError(
                f"selenium failed to convert {input_file_url} to {output_abspath}"
            )
