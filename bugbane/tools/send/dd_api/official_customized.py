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

# Partially overwrites original class DefectDojoAPI in
# defectdojo_api library which is licensed under the MIT License
# For more details on defectdojo_api visit https://github.com/DefectDojo/defectdojo_api

import json
import requests

from defectdojo_api.defectdojo_apiv2 import DefectDojoAPIv2

from .abc import DefectDojoAPIError, DefectDojoResponse
from .factory import DefectDojoAPIFactory
from .official import DefectDojoAPI_official


@DefectDojoAPIFactory.register("official_customized")
class DefectDojoAPI_official_customized(DefectDojoAPI_official):
    def instantiate_underlying_api(self):
        self.api = CustomDefectDojoAPIv2(
            self.host,
            self.user_token,
            self.user_name,
            debug=self.debug,
            verify_ssl=self.verify_ssl,
            api_version="v2",
        )


class CustomDefectDojoAPIv2(DefectDojoAPIv2):
    def _request(self, method, url, params=None, data=None, files=None):
        """Common handler for all HTTP requests."""
        if not params:
            params = {}

        headers = {
            "User-Agent": self.user_agent,
            "Authorization": (
                ("ApiKey " + self.user + ":" + self.api_token)
                if (self.api_version == "v1")
                else ("Token " + self.api_token)
            ),
        }

        # if data:
        # data = json.dumps(data)

        if not files:
            headers["Accept"] = "application/json"
            headers["Content-Type"] = "application/json"

            # custom change: make data json only if there were no files
            if data:
                data = json.dumps(data)

        if self.proxies:
            proxies = self.proxies
        else:
            proxies = {}

        try:
            self.logger.debug("request:")
            self.logger.debug(method + " " + url)
            self.logger.debug("headers: " + str(headers))
            self.logger.debug("params:" + str(params))
            self.logger.debug("data:" + str(data))
            self.logger.debug("files:" + str(files))

            response = requests.request(
                method=method,
                url=self.host + url,
                params=params,
                data=data,
                files=files,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                cert=self.cert,
                proxies=proxies,
            )

            self.logger.debug("response:")
            self.logger.debug(response.status_code)
            self.logger.debug(response.text)

            try:
                if response.status_code == 201:  # Created new object
                    try:
                        object_id = response.headers["Location"].split("/")
                        key_id = object_id[-2]
                        data = int(key_id)
                    except:
                        data = response.json()

                    return DefectDojoResponse(
                        message="Upload complete",
                        response_code=response.status_code,
                        data=data,
                        success=True,
                    )
                elif response.status_code == 204:  # Object updates
                    return DefectDojoResponse(
                        message="Object updated.",
                        response_code=response.status_code,
                        success=True,
                    )
                elif response.status_code == 400:  # Object not created
                    return DefectDojoResponse(
                        message="Error occured in API.",
                        response_code=response.status_code,
                        success=False,
                        data=response.text,
                    )
                elif response.status_code == 404:  # Object not created
                    return DefectDojoResponse(
                        message="Object id does not exist.",
                        response_code=response.status_code,
                        success=False,
                        data=response.text,
                    )
                elif response.status_code == 401:
                    return DefectDojoResponse(
                        message="Unauthorized.",
                        response_code=response.status_code,
                        success=False,
                        data=response.text,
                    )
                elif response.status_code == 414:
                    return DefectDojoResponse(
                        message="Request-URI Too Large.",
                        response_code=response.status_code,
                        success=False,
                    )
                elif response.status_code == 500:
                    return DefectDojoResponse(
                        message="An error 500 occured in the API.",
                        response_code=response.status_code,
                        success=False,
                        data=response.text,
                    )
                else:
                    data = response.json()
                    return DefectDojoResponse(
                        message="Success",
                        data=data,
                        success=True,
                        response_code=response.status_code,
                    )
            except ValueError:
                return DefectDojoResponse(
                    message="JSON response could not be decoded.",
                    response_code=response.status_code,
                    success=False,
                    data=response.text,
                )
        except requests.exceptions.SSLError:
            self.logger.warning("An SSL error occurred.")
            return DefectDojoResponse(
                message="An SSL error occurred.",
                response_code=response.status_code,
                success=False,
            )
        except requests.exceptions.ConnectionError:
            self.logger.warning("A connection error occurred.")
            return DefectDojoResponse(
                message="A connection error occurred.",
                response_code=response.status_code,
                success=False,
            )
        except requests.exceptions.Timeout:
            self.logger.warning("The request timed out")
            return DefectDojoResponse(
                message="The request timed out after "
                + str(self.timeout)
                + " seconds.",
                response_code=response.status_code,
                success=False,
            )
        except requests.exceptions.RequestException as e:
            self.logger.warning("There was an error while handling the request.")
            self.logger.exception(e)
            return DefectDojoResponse(
                message="There was an error while handling the request.",
                response_code=response.status_code,
                success=False,
            )
