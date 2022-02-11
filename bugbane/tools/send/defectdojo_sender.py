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

from typing import Dict
import os
import json
from datetime import datetime

import logging

log = logging.getLogger(__name__)

from .dd_api.abc import DefectDojoAPI, DefectDojoAPIError


class DefectDojoSender:
    """
    Loads JSON issue cards
    Optionaly translates sample paths
    Uploads findings using DefectDojoAPI
    """

    def __init__(self, api: DefectDojoAPI, translate_sample_paths_arg, cards_file_path):
        """
        api: initialized DefectDojoAPI
        translate_sample_paths_arg: --tsp arg straight from ArgumentParser.parse_args()
        cards_file_path: path to json file with issue cards (findings)
        """

        self.translate_sample_paths_argument = translate_sample_paths_arg
        self.cards_file_path = cards_file_path

        self.issue_cards = []

        self.sample_path_translation_map = self.__make_sample_path_translation_map()

        self.api = api

    @staticmethod
    def __try_load_json(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)

    def load_cards(self):
        """
        Loads issue cards and fuzz_stats from json file passed in --results-file
        """

        try:
            jsondata = self.__try_load_json(self.cards_file_path)
            self.issue_cards = jsondata["issue_cards"]
            self.fuzz_stats = jsondata["fuzz_stats"]
        except KeyError as e:
            raise DefectDojoAPIError(
                f"ERROR while processing file '{self.cards_file_path}': JSON data doesn't contain 'issue_cards' and/or 'fuzz_stats' fields"
            ) from e
        except ValueError as e:
            raise DefectDojoAPIError(
                f"ERROR: while decoding file '{self.cards_file_path}'. Message: {e}"
            ) from e
        except OSError as e:
            raise DefectDojoAPIError(
                f"ERROR: while loading json from file '{self.cards_file_path}'. Message: {e}"
            ) from e

        self.__translate_all_sample_paths()

    def create_dd_findings(self):
        if not self.issue_cards:
            log.warning("no findings to create as issue cards array is empty")
            return

        self.api.create_test()

        for card in self.issue_cards:
            finding_id, resp = self.__create_one_dd_finding(card)

            if finding_id is None:
                log.warning("wasn't able to create finding from the following card:")
                log.warning(card)
                log.warning("API response was: %s", resp)
                continue

            log.info("Created finding: %s", self.api.make_finding_url(finding_id))

            # FIXME: sample uploading
            # file_title = self.__make_finding_sample_title(finding_id, card["sample"])
            # upload_ok = self.api.upload_file_for_finding(
            #     finding_id, file_title, card["sample"]
            # )
            # log.verbose2(
            #     "File upload result:", {False: "FAIL", True: "Success"}[upload_ok]
            # )

    def __create_one_dd_finding(self, issue_card):
        """
        Creates a finding from issue card using DefectDojoAPI
        """

        description = self.__make_finding_description(issue_card)

        f = issue_card

        finding_id = self.api.create_finding(
            title=f["title"],
            description=description,
            severity="Critical",
            numerical_severity="S0",
            impact="Confidentiality, Integrity, Accessibility",
            cwe=20,
            file_path=f.get("file"),
            line=f.get("line"),
            unique_id_from_tool=f["title"],
            vuln_id_from_tool=f.get("verdict"),
            references="https://github.com/google/sanitizers",
        )
        return finding_id

    def __make_finding_description(self, issue_card):

        if not issue_card:
            return "<<-- No description -->>"

        description = "While running test sample %s on application %s:\n```\n%s\n\n%s\n```" % (
            issue_card["sample"],
            issue_card["binary"],
            # TODO: this should go to "steps to reproduce"
            issue_card["reproduce_cmd"],
            issue_card["output"],
        )

        env = issue_card.get("reproduce_env")
        if env:
            description += "\nEnvironment was:\n" + env

        return description

    def __make_sample_path_translation_map(self):
        """
        Creates self.sample_path_translation_map dictionary
        based on options of --translate-sample-paths
        """

        result = {}
        if not self.translate_sample_paths_argument:
            return result

        for rule in self.translate_sample_paths_argument:
            self.__add_path_translation_rule(result, rule)

        return result

    def __add_path_translation_rule(self, result_dict: Dict[str, str], rule: str):
        """
        Splits rule to old and new path parts,
        checks them for common errors,
        appends parts to result_dict
        """

        sep = "->"  # rule separator

        try:
            old, new = rule.split(sep, 1)
        except ValueError:
            log.warning(
                "in path translation rule '%s': not enough elements separated by '%s' - RULE IGNORED",
                rule,
                sep,
            )
            return

        if not old or not new:
            log.warning(
                "in path translation rule '%s': old or new path is empty - RULE IGNORED",
                rule,
            )
            return

        if old in result_dict:
            log.warning(
                "in path translation rule '%s': old part '%s' was already defined - RULE IGNORED",
                rule,
                old,
            )
            return

        result_dict[old] = new

    def __translate_all_sample_paths(self):
        """
        Change sample file paths in self.issue_cards based on --translate-sample-paths.
        Check if new paths exist, otherwise append "ignore_file_upload" flag to corresponding issue cards
        """

        if not self.sample_path_translation_map:
            return

        for card in self.issue_cards:
            path = card["sample"]
            path = self.__translate_sample_path(path)
            ignore_file_upload = not os.path.isfile(path)
            card["ignore_file_upload"] = ignore_file_upload
            if ignore_file_upload:
                log.warning(
                    "during path translation: no file with new path exist: '%s' (old path was '%s'). File won't be uploaded!",
                    path,
                    card["sample"],
                )

            card["sample"] = path

    def __translate_sample_path(self, path):
        """
        Performs changes in path based on self.sample_path_translation_map
        """

        if not path or not self.sample_path_translation_map:
            return path

        for old, new in self.sample_path_translation_map.items():
            path = path.replace(old, new)

        return path

    def __make_finding_sample_title(self, finding_id, file_path):
        """
        Makes unique title for sample file to be uploaded to Defect Dojo
        """
        if not file_path:
            return file_path

        basename = os.path.basename(file_path)
        date_and_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return "%s__%d__%s" % (date_and_time, finding_id, basename)
