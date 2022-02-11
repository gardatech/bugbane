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

from dataclasses import asdict
from typing import Optional, List, Dict

import os
import logging


log = logging.getLogger(__name__)

from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory
from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo

from .reproducers.factory import ReproducerFactory
from .reproducers.reproducer import Reproducer

from .results import TotalReproduceResult
from .issue_card import IssueCard


class HarvesterError(Exception):
    """Class for errors that happen in Harvester class"""


class Harvester:
    def __init__(self):
        self.fuzz_stats: Optional[FuzzStats] = None
        self.issue_cards: Dict[str, IssueCard] = {}

        self.specs: Optional[List[List[str]]] = None
        self.run_args: Optional[List[str]] = None
        self.run_env: Optional[Dict[str, str]] = None
        self.hang_timeout_sec: float = 10.0
        self.result = TotalReproduceResult()
        self.num_reruns: int = 3
        self.use_abspath: bool = False
        self.src_path_base: Optional[str] = None

    def set_specs(self, specs: List[List[str]]):
        """Save spec to self.specs"""
        self.specs = specs

    def set_run_args(self, run_args: List[str]):
        """Save run_args to self.run_args"""
        self.run_args = run_args

    def set_run_env(self, run_env: Dict[str, str]):
        """Save run_env to self.run_env"""
        self.run_env = run_env
        cur_env = os.environ.copy()
        appendables_semicolon = {
            "ASAN_OPTIONS",
            "UBSAN_OPTIONS",
            "LD_PRELOAD",
            "LD_LIBRARY_PATH",
            "PATH",
        }

        for var in appendables_semicolon:
            if var not in cur_env:
                continue
            if var not in self.run_env:
                self.run_env[var] = cur_env[var]
            else:
                self.run_env[var] += ":" + cur_env[var]

    def set_hang_timeout(self, milliseconds: int):
        """Save milliseconds to self.run_env as seconds"""
        self.hang_timeout_sec = milliseconds / 1000.0

    def set_num_reruns(self, num_reruns: int):
        """Save num_reruns to self.num_reruns"""
        self.num_reruns = num_reruns

    def set_use_abspath(self, use_abspath: bool):
        """Save use_abspath to self.use_abspath"""
        self.use_abspath = use_abspath

    def set_src_path_base(self, src_path: Optional[str]):
        self.src_path_base = src_path

    def collect_fuzzing_results(self) -> dict:
        """
        Loads generic fuzzing stats, reproduces samples on binaries.
        Returns dict consisting of fuzzing stats and issue cards
        """

        if not self.specs:
            raise HarvesterError("specs not set")

        log.verbose2("Reproducing with env vars: %s", self.run_env)

        self.fuzz_stats = None

        for fuzzer_dir_and_builds in self.specs:
            spec_name = "'" + " ".join(fuzzer_dir_and_builds) + "'"
            log.verbose1("Checking spec %s...", spec_name)

            fuzzer_and_syncdir = fuzzer_dir_and_builds[0]
            fuzzer_type, sync_dir = fuzzer_and_syncdir.split(":", 1)

            build_specs = fuzzer_dir_and_builds[1:]

            self.collect_one_spec_fuzzing_results(fuzzer_type, sync_dir, build_specs)

        if self.issue_cards:
            log.verbose1(
                "ISSUE CARDS: \nTITLE: "
                + "\nTITLE: ".join(title for title in self.issue_cards)
            )

        return self.cards_to_dict()

    def collect_one_spec_fuzzing_results(
        self, fuzzer_type: str, sync_dir: str, build_specs: List[str]
    ):
        """
        For one spec (fuzzer <-> sync_dir & build <-> subdir) reproduce
        crashes and hangs. Store reportable results to self.issue_cards
        """
        log.verbose1("Checking path %s (%s)", sync_dir, fuzzer_type)
        try:
            fuzzer_info: FuzzerInfo = FuzzerInfoFactory.create(fuzzer_type)
            reproducer: Reproducer = ReproducerFactory.create(fuzzer_type)
        except TypeError as e:
            raise HarvesterError(
                f"while trying to use fuzzer_type={fuzzer_type}: {e}"
            ) from e

        self.add_stats(self.load_stats(fuzzer_type, fuzzer_info.stats_dir(sync_dir)))
        for app_and_dir in build_specs:
            binary_path, instance_path = app_and_dir.split(":", 1)
            log.verbose2(
                "Will search for crashes and hangs in directory '%s' for app '%s'",
                instance_path,
                binary_path,
            )

            crashes_path_mask = fuzzer_info.crash_mask(sync_dir, instance_path)
            hangs_path_mask = fuzzer_info.hang_mask(sync_dir, instance_path)

            log.trace("sync_dir=%s, instance_path=%s", sync_dir, instance_path)
            log.verbose2(
                "Sample masks: '%s' (crashes) and '%s' (hangs)",
                crashes_path_mask,
                hangs_path_mask,
            )
            cards = reproducer.run_binary_on_samples(
                binary_path, crashes_path_mask, hangs_path_mask
            )
            self.add_reproduce_issue_cards(cards)

    def add_reproduce_issue_cards(self, cards: List[IssueCard]):
        """Add cards to self.issue_cards while creating issue titles"""
        for card in cards:
            card.load_location_and_set_title(self.src_path_base)
            if card.title not in self.issue_cards:
                self.issue_cards[card.title] = card

    def load_stats(self, fuzzer_type: str, sync_dir: str) -> FuzzStats:
        """
        Load fuzzer stats from specified `sync_dir`
        """
        try:
            fuzz_stats: FuzzStats = FuzzStatsFactory.create(fuzzer_type)
        except TypeError as e:
            raise HarvesterError(
                f"failed to create FuzzStats object of type {fuzzer_type}"
            ) from e

        fuzz_stats.load(sync_dir)
        return fuzz_stats

    def add_stats(self, stats: FuzzStats):
        if self.fuzz_stats is None:
            self.fuzz_stats = stats
        else:
            self.fuzz_stats.add_stats_from(stats)

    def cards_to_dict(self) -> dict:
        """
        Convert self.issue_cards: dict[title: str, card: IssueCard] to dict[issue_key: str, issue_value: str]
        Return resulting dict
        """
        result = {}
        cards = []

        for _, v in self.issue_cards.items():
            d = asdict(v)
            d.update({"verdict": v.verdict.name})
            cards.append(d)

        result["issue_cards"] = cards

        if self.fuzz_stats is not None:
            result["fuzz_stats"] = asdict(self.fuzz_stats)

        return result
