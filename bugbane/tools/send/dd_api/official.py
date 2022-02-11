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

# Inherits from original DefectDojoAPI class from
# defectdojo_api library which is licensed under the MIT License
# For more details on defectdojo_api visit https://github.com/DefectDojo/defectdojo_api

from typing import Optional, Tuple

import os
import json
from datetime import datetime

from defectdojo_api.defectdojo_apiv2 import DefectDojoAPIv2 as ddapiv2_official

from .abc import DefectDojoAPI, DefectDojoAPIError, DefectDojoResponse
from .factory import DefectDojoAPIFactory


@DefectDojoAPIFactory.register("official")
class DefectDojoAPI_official(DefectDojoAPI):
    """
    Implementation based on use of defectdojo_api library
    """

    def __init__(self):
        super().__init__()
        self.api: Optional[ddapiv2_official] = None

    def instantiate_api(
        self,
        host: str,
        verify_ssl: bool,
        user_name: str,
        user_id: int,
        user_token: str,
        user_password: str,
        engagement_id: int,
        test_type_id: int,
        debug: bool = False,
    ):
        super().instantiate_api(
            host,
            verify_ssl,
            user_name,
            user_id,
            user_token,
            user_password,
            engagement_id,
            test_type_id,
            debug,
        )

        self.instantiate_underlying_api()
        self.__check_connectivity_or_raise()
        self.load_product_id()

    def instantiate_underlying_api(self):
        self.api = ddapiv2_official(
            self.host,
            self.user_token,
            self.user_name,
            debug=self.debug,
            verify_ssl=self.verify_ssl,
            api_version="v2",
        )

    def __check_connectivity_or_raise(self):
        if not self.check_connection():
            raise DefectDojoAPIError(
                f"No API connectivity with DefectDojo host '{self.host}'"
            )

    def check_connection(self):
        user = self.api.get_user(1)
        return user.message == "Success"

    def load_product_id(self):
        engagement_resp = self.api.get_engagement(self.engagement_id)
        if engagement_resp.response_code == -1:
            return

        self.product_id = self.__get_value_from_dd_response(engagement_resp, "product")

    def create_test(self) -> int:
        """
        Create new test in corresponding engagement,
        set test id instance variable, return test id
        """

        # TODO: extract actual fuzzing start time
        date_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_end = date_start

        test_id_resp = self.api.create_test(
            engagement_id=self.engagement_id,
            target_start=date_start,
            target_end=date_end,
            test_type=self.test_type_id,
            percent_complete=100,
            environment=1,  # 1 = Development
        )

        self.test_id = self.__get_id_from_dd_response(test_id_resp)
        return self.test_id

    def __get_value_from_dd_response(self, response, key):
        if not response or not key:
            return None

        data = response.data_json()
        jsondata = json.loads(data)

        try:
            value = jsondata.get(key)
        except AttributeError:
            value = None

        return value

    def __get_id_from_dd_response(self, response):
        return self.__get_value_from_dd_response(response, "id")

    def create_finding(
        self,
        title: str,
        description: str,
        severity: str,
        numerical_severity: str,
        cwe: int,
        active: bool = True,
        verified: bool = True,
        static_finding: bool = False,
        dynamic_finding: bool = True,
        file_path: Optional[str] = None,
        line: Optional[int] = None,
        unique_id_from_tool: Optional[str] = None,
        vuln_id_from_tool: Optional[str] = None,
        **kwargs,
    ) -> Tuple[int, DefectDojoResponse]:
        """
        Same implementation as in DefectDojoAPIv2.create_finding,
        but also append 'found_by', 'unique_id_from_tool' and 'vuln_id_from_tool' fields to data
        """

        # TODO: use detection date instead of upload date?
        date = kwargs.get("date", datetime.now().strftime("%Y-%m-%d"))

        data = {
            "title": title,
            "description": description,
            "severity": severity,
            "numerical_severity": numerical_severity,
            "cwe": cwe,
            "date": date,
            "product": self.product_id,
            "engagement": self.engagement_id,
            "test": self.test_id,
            "reporter": self.user_id,
            "active": active,
            "verified": verified,
            "line": line,
            "file_path": file_path,
            "static_finding": static_finding,
            "dynamic_finding": dynamic_finding,
            "found_by": [self.test_type_id],
            "unique_id_from_tool": unique_id_from_tool,
            "vuln_id_from_tool": vuln_id_from_tool,
        }

        default_values = {
            "impact": None,
            "mitigation": None,
            "references": None,
            "build_id": None,
            "false_p": False,
            "duplicate": False,
            "out_of_scope": False,
            "under_review": False,
            "under_defect_review": False,
        }
        data.update(default_values)

        for k in default_values:
            if k in kwargs:
                data[k] = kwargs[k]

        # if endpoints field present in request, it shouldn't be None
        endpoints = kwargs.get("endpoints")
        if endpoints is not None:
            data.update({"endpoints": endpoints})

        resp = self.api._request("POST", "findings/", data=data)
        id = self.__get_id_from_dd_response(resp)

        return (id, resp)

    def upload_file_for_finding(
        self, finding_id: int, file_title: str, file_path: str
    ) -> bool:
        """
        Note: file title should be unique across the whole Defect Dojo database
        """

        if not os.path.isfile(file_path):
            raise DefectDojoAPIError(
                f"file '{file_path}' couldn't be uploaded for finding '{self.make_finding_url(finding_id)}' because it doesn't exist"
            )

        try:
            with open(file_path, "rb") as f:
                filedata = f.read()
        except OSError as e:
            raise DefectDojoAPIError(
                f"wasn't able to read file '{file_path}', so it can't be uploaded for finding '{self.make_finding_url(finding_id)}'"
            ) from e

        data = {
            "title": (None, file_title, "application/json"),
            "file": (file_title, filedata, "application/octet-stream"),
        }
        resp = self.api._request(
            "POST",
            f"findings/{finding_id}/files",
            # f"manage_files/{finding_id}/Finding",
            files=data,
        )

        return resp.response_code == 200
