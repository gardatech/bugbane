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

"""
Module describes generic interface of DefectDojoAPI
and base exception type DefectDojoAPIError.
"""

from typing import Optional, Tuple
from abc import ABC, abstractmethod

from defectdojo_api.defectdojo_apiv2 import DefectDojoResponse


class DefectDojoAPIError(Exception):
    """
    Exception type for generic errors in DefectDojoAPI
    """


class DefectDojoAPI(ABC):
    """
    ABC for DefectDojo API.
    One instantiated object should be reusable for creating new tests, findings, etc.
    Note: this class is not fully abstract, as it implements some methods
    """

    def __init__(self):
        self.host: Optional[str] = None
        self.verify_ssl: bool = True
        self.user_name: Optional[str] = None
        self.user_id: Optional[int] = None
        self.user_token: Optional[str] = None
        self.user_password: Optional[str] = None
        self.product_id: Optional[int] = None
        self.engagement_id: Optional[int] = None
        self.test_type_id: Optional[int] = None
        self.debug: bool = False
        self.test_id: Optional[int] = None

    @abstractmethod
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
        """
        Initialize this object fields, make required connections, etc.
        Throw DefectDojoAPIError in case of failure
        """

        self.host = host
        self.verify_ssl = verify_ssl
        self.user_name = user_name
        self.user_id = user_id
        self.user_token = user_token
        self.user_password = user_password
        self.engagement_id = engagement_id
        self.test_type_id = test_type_id
        self.debug = debug
        self.test_id = None

    @abstractmethod
    def instantiate_underlying_api(self):
        """
        Initialize underlying API
        """

    @abstractmethod
    def check_connection(self) -> bool:
        """
        Check if we can execute methods against DefectDojo instance.
        Return True on success
        """

    @abstractmethod
    def create_test(self) -> int:
        """
        Create new test,
        store test id as instance variable self.test_id,
        return test id
        """

    @abstractmethod
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
        Create new finding, return tuple: (finding id, DefectDojoResponse)
        """

    @abstractmethod
    def upload_file_for_finding(
        self, finding_id: int, file_title: str, file_path: str
    ) -> bool:
        """
        Upload a file for given finding.
        Return True on success
        """

    @abstractmethod
    def load_product_id(self):
        """
        Set product id instance variable corresponding to previosly saved engagement id.
        """

    def make_finding_url(self, finding_id: int):
        """
        Converts finding_id to full host url
        """

        if finding_id is None:
            return None

        return self.host + "/finding/" + str(finding_id)
