# Copyright 2022-2025 Garda Technologies, LLC. All rights reserved.
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

from dataclasses import asdict, dataclass, field, fields
from typing import Optional, List, Dict, Any, Sequence, Iterable, Tuple, Union

import os
import glob
import shlex
import fnmatch

from bugbane.errors import BugBaneException
from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory
from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats

# XXX: it's a poor decision to import specific implementation directly
#      but it's only used to hold previously saved fuzz stats, when we
#      don't have our own stats
from bugbane.modules.stats.fuzz.aflplusplus import AFLplusplusFuzzStats

from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo
from bugbane.modules.process import (
    make_env_shell_str,
    make_env_dict_from_str,
    ProcessException,
)

from bugbane.modules.file_utils import FileUtilsException, load_dict_from_json_file

from .reproducers.factory import ReproducerFactory
from .reproducers.reproducer import Reproducer

from .results import ReproduceStats
from .issue_card import IssueCard
from .verdict import Verdict


class HarvesterError(BugBaneException):
    """Class for errors that happen in Harvester class."""


@dataclass
class ReproduceSettings:
    """
    The dataclass describing the reproduce procedure settings
    such as number of attempts to trigger a bug.
    """

    hang_reproduce_limit: int = 3
    num_reruns: int = 3
    use_abspath: bool = False
    src_path_base: Optional[str] = None


@dataclass
class AppConfig:
    """
    A dataclass describing the application under test.
    Contains information on what binaries to run and how to run them
    """

    specs: Optional[List[List[str]]] = None
    run_args: Optional[List[str]] = None
    run_env: Dict[str, str] = field(default_factory=dict)
    hang_timeout_sec: float = 10.0

    def __post_init__(self) -> None:
        self.merge_run_env_with_os_env()

    def merge_run_env_with_os_env(self) -> None:
        """
        Merge the vars provided in `self.run_env` with matching
        environment variables already defined for current process.
        """
        cur_env = os.environ.copy()
        appendables_colon = {
            "ASAN_OPTIONS",
            "UBSAN_OPTIONS",
            "LD_PRELOAD",
            "LD_LIBRARY_PATH",
            "PATH",
        }

        for var in appendables_colon:
            if var not in cur_env:
                continue
            if var not in self.run_env:
                self.run_env[var] = cur_env[var]
            else:
                self.run_env[var] += ":" + cur_env[var]


class Harvester:
    """
    High level class that collects fuzz stats and reproduces bugs.
    """

    def __init__(
        self, reproduce_settings: ReproduceSettings, app_config: AppConfig
    ) -> None:
        self.reproduce_settings = reproduce_settings
        self.app_config = app_config

        self.fuzz_stats: Optional[FuzzStats] = None
        self.issue_cards: Dict[str, IssueCard] = {}
        self.reproduce_stats = ReproduceStats()

    def collect_fuzzing_results(
        self,
        saved_results_file_path: Optional[str],
        old_bugs_masks: Optional[Sequence[str]] = None,
        extra_bugs_masks: Optional[Sequence[str]] = None,
        no_own_bugs: bool = False,
    ) -> Dict[str, Any]:
        """
        Loads generic fuzzing stats, reproduces samples on binaries.
        Returns dict consisting of fuzzing stats and issue cards
        """
        if (
            not self.app_config.specs
            and not old_bugs_masks
            and not self.app_config.run_args
        ):
            raise HarvesterError(
                "specs, old bugs masks, and program run args are all not set. Can't determine app builds and how to run them"
            )

        log.verbose2(
            "Reproducing with env vars: %s",
            make_env_shell_str(self.app_config.run_env) or "<none>",
        )

        reproduce_own_bugs = not no_own_bugs

        # NOTE: when we reproduce own bugs multiple times, we only keep the last own stats.
        #       Otherwise we'd need some sophisticated way to sum these stats.
        #       But when there's --no-own-bugs, we should keep self.fuzz_stats here
        if reproduce_own_bugs:
            self.fuzz_stats = None

        if self.app_config.specs and reproduce_own_bugs:
            log.info("Reproducing newfound bugs in fuzzer sync dir (if any)...")
            for fuzzer_dir_and_builds in self.app_config.specs:
                spec_name = " ".join(fuzzer_dir_and_builds)
                log.verbose1("Checking spec '%s'...", spec_name)

                fuzzer_and_syncdir = fuzzer_dir_and_builds[0]
                fuzzer_type, sync_dir = fuzzer_and_syncdir.split(":", 1)

                build_specs = fuzzer_dir_and_builds[1:]

                self.collect_one_spec_fuzzing_results(
                    fuzzer_type, sync_dir, build_specs
                )

        log.info("Reproducing additional bugs outside fuzzer sync dir (if any)...")

        self.reproduce_additional_bugs(
            saved_results_file_path=saved_results_file_path,
            old_bugs_masks=old_bugs_masks,
            extra_bugs_masks=extra_bugs_masks,
        )

        if self.issue_cards:
            message = "ISSUES:"
            for index, title in enumerate(self.issue_cards, start=1):
                message += f"\n{index}. {title}"
            log.info(message)

        return self.issue_cards_to_dict()

    def collect_one_spec_fuzzing_results(
        self, fuzzer_type: str, sync_dir: str, build_specs: List[str]
    ) -> None:
        """
        For one spec (fuzzer <-> sync_dir & build <-> subdir) reproduce
        crashes and hangs. Store reportable results to `self.issue_cards`
        """
        log.verbose1("Checking path %s (%s)", sync_dir, fuzzer_type)
        try:
            fuzzer_info: FuzzerInfo = FuzzerInfoFactory.create(fuzzer_type)
            reproducer = self.make_reproducer(fuzzer_info)
        except TypeError as e:
            raise HarvesterError(
                f"while trying to use fuzzer_type={fuzzer_type}: {e}"
            ) from e

        self.add_stats(self.load_stats(fuzzer_type, fuzzer_info.stats_dir(sync_dir)))

        for app_and_dir in build_specs:
            binary_path, instance_path = app_and_dir.split(":", 1)
            log.verbose2(
                "Will search for crashes and hangs for sync directory '%s' for app '%s'",
                instance_path,
                binary_path,
            )
            log.trace("sync_dir=%s, instance_path=%s", sync_dir, instance_path)

            crashes_mask = fuzzer_info.crash_mask(sync_dir, instance_path)
            hangs_mask = fuzzer_info.hang_mask(sync_dir, instance_path)

            if hangs_mask:
                log.verbose2(
                    "Sample masks: '%s' (crashes) and '%s' (hangs)",
                    crashes_mask,
                    hangs_mask,
                )
            else:
                log.verbose2("Sample masks: '%s' (crashes)", crashes_mask)

            cards = reproducer.run_binary_on_samples(
                binary_path,
                glob.iglob(crashes_mask),
                glob.iglob(hangs_mask),
                self.reproduce_settings.hang_reproduce_limit,
            )
            self.add_reproduce_issue_cards(cards)

    def make_reproducer(self, fuzzer_info: FuzzerInfo) -> Reproducer:
        """
        Create and configure reproducer for the specified `fuzzer_info`
        """
        fuzzer_type = fuzzer_info.fuzzer_type_name()
        try:
            reproducer: Reproducer = ReproducerFactory.create(fuzzer_type)
        except TypeError as e:
            raise HarvesterError(
                f"while trying to use fuzzer_type={fuzzer_type}: {e}"
            ) from e

        if self.app_config.run_args is None:
            raise HarvesterError(f"run_args not set")

        repro_run_args = fuzzer_info.one_sample_run_args(self.app_config.run_args)
        reproducer.set_run_args(repro_run_args)
        reproducer.set_run_env(self.app_config.run_env)
        reproducer.set_num_tries(self.reproduce_settings.num_reruns)
        return reproducer

    def add_reproduce_issue_cards(self, cards: List[IssueCard]):
        """Add cards to self.issue_cards while creating issue titles"""
        for card in cards:
            card.load_location_and_set_title(self.reproduce_settings.src_path_base)
            title = card.title
            if title is None:
                continue
            if title == "Hang":
                continue  # ignore false positive hangs (no location detected)
            if title in self.issue_cards:
                if card.is_old:
                    self.issue_cards[title].is_old = True
                if card.is_extra:
                    self.issue_cards[title].is_extra = True
            else:
                self.issue_cards[title] = card

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

    def add_stats(self, stats: FuzzStats) -> None:
        """
        Append `stats` to `self.fuzz_stats`.
        """
        if self.fuzz_stats is None:
            self.fuzz_stats = stats
        else:
            self.fuzz_stats.add_stats_from(stats)

    def issue_cards_to_dict(self) -> Dict[str, Any]:
        """
        Convert `self.issue_cards` from dict of IssueCard to dict of basic types.
        Return resulting dict
        """
        result: Dict[str, Any] = {}
        cards: List[Dict[str, str]] = []

        for _, v in self.issue_cards.items():
            if v.verdict is None:
                continue
            d = asdict(v)
            d.update({"verdict": v.verdict.name})
            cards.append(d)

        result["issue_cards"] = cards

        if self.fuzz_stats is not None:
            result["fuzz_stats"] = asdict(self.fuzz_stats)

        return result

    def load_existing_results_file(self, results_file_path: str) -> None:
        """
        Try to load existing bugbane results file from disk.
        This includes issues and fuzz stats.

        In case of fatal errors, raise HarvesterError.
        Do nothing if the file doesn't exist.
        """
        if not os.path.isfile(results_file_path):
            return

        try:
            log.info(
                "Have found and will try to load existing results file: %s",
                results_file_path,
            )
            data = load_dict_from_json_file(results_file_path)
        except FileUtilsException as e:
            raise HarvesterError(
                f"wasn't able to load existing bugbane results file: {e}"
            )

        self.add_issues_from_results_dict(data)

    def add_issues_from_results_dict(self, results_file_dict: Dict[str, Any]) -> None:
        """
        Convert `results_file_dict` to dict[str, IssueCard] and append this
        result to `self.issue_cards`.
        """

        if "fuzz_stats" in results_file_dict:
            if self.fuzz_stats is None:
                try:
                    self.fuzz_stats = AFLplusplusFuzzStats(
                        **results_file_dict["fuzz_stats"]
                    )
                except TypeError as e:
                    raise HarvesterError(
                        f"failed to load fuzz stats from existing bugbane results file, error message: {e}"
                    ) from e
            else:
                log.warning(
                    "ignoring fuzz stats present in existing bugbane results file, because we have our own fuzz stats"
                )

        issues_field = "issue_cards"

        if issues_field not in results_file_dict:
            log.warning(
                'existing bugbane results file does not have the "%s" field - no issues loaded',
                issues_field,
            )
            return

        raw_issues_list = results_file_dict[issues_field]
        issues = self.dict_to_issue_cards(raw_issues_list)

        if len(issues) < 1:  # nothing to add, so just leave
            return

        for index, loaded_issue in enumerate(issues, start=1):
            if not loaded_issue.title:
                log.warning(
                    "loading existing bugbane results file: invalid issue #%d: has no title - ISSUE SKIPPED",
                    index,
                )
                continue

            title = loaded_issue.title
            if title not in self.issue_cards:
                self.issue_cards[title] = loaded_issue
            elif loaded_issue.is_old:
                # set flag and ignore the rest data from old issue
                # because current output of tested app is more relevant
                self.issue_cards[title].is_old = True
                self.issue_cards[title].is_extra = loaded_issue.is_extra
            elif loaded_issue.is_extra:
                # not new and not old, just extra: append to issues
                self.issue_cards[title] = loaded_issue

    @staticmethod
    def dict_to_issue_cards(issues: List[Dict[str, Any]]) -> List[IssueCard]:
        """
        Convert `issues` to a list of `IssueCard`.
        `issues` here is the "issue_cards" list in the results file.
        """
        allowed_fields = {field.name or field.type for field in fields(IssueCard)}
        results: List[IssueCard] = []
        for index, issue in enumerate(issues, start=1):
            try:
                # XXX: no sanitization here, so types may get messy if results file has been tampered with
                card = IssueCard(
                    **{k: v for k, v in issue.items() if k in allowed_fields}
                )

                # restore proper verdict object from its name
                card.verdict = Verdict.from_string(card.verdict)  # type: ignore

                results.append(card)
            except TypeError as e:
                log.warning("wasn't able to read the issue #%d, error: %s", index, e)

        return results

    def reproduce_additional_bugs(
        self,
        saved_results_file_path: Optional[str],
        old_bugs_masks: Optional[Sequence[str]],
        extra_bugs_masks: Optional[Sequence[str]],
    ) -> None:
        """
        Reproduce bugs the samples for which cannot be found under bugbane-controlled fuzzer's sync dir.
        Used for regression testing (`old_bugs_masks`) and for testing on a custom user provided samples (`extra_bugs_masks`).
        It is assumed that `old_bugs_masks` lead to bugs, discovered by previous fuzzing campaigns,
        and `extra_bugs_masks` lead to bugs, found in current fuzzing campaign, but not residing in the sync directory of a
        fuzzer controlled by bb-fuzz
        """

        self.reproduce_old_bugs(
            saved_results_file_path=saved_results_file_path, sample_masks=old_bugs_masks
        )
        self.reproduce_extra_bugs(extra_bugs_masks)

    def reproduce_old_bugs(
        self,
        saved_results_file_path: Optional[str],
        sample_masks: Optional[Sequence[str]],
    ) -> None:
        """
        Find previously saved bug samples along with the bugbane results files.
        Reproduce bugs.

        Expected `sample_masks` format (example):
            [ "storage/fuzz_target/*/bug_samples/*", ... ]
        If `saved_results_file_path` is "../../bb_results.json", then
        for this example it is assumed that the "storage/fuzz_target/*/bb_results.json" files exist.
        """

        log.debug(
            "saved_results_file_path=%r, sample_masks=%r",
            saved_results_file_path,
            sample_masks,
        )

        if not sample_masks:
            return

        if not saved_results_file_path:
            return

        log.info(
            "Reproducing OLD bugs outside fuzzer sync dir, sample masks: %s",
            ", ".join(sample_masks or []) or "<none>",
        )

        restore_app_config = not self.app_config.specs

        reproducers_cache: Dict[str, Reproducer] = {}

        for mask in sample_masks:
            log.debug("mask=%s", mask)
            parts = saved_results_file_path.split(os.sep)
            if ".." not in parts:
                saved_results_file_path = os.path.join("..", saved_results_file_path)
            results_file_mask = os.path.normpath(
                os.path.join(mask, saved_results_file_path)
            )
            log.debug("results_file_mask=%s", results_file_mask)

            for results_file_path in glob.iglob(results_file_mask):
                log.debug("results_file_path=%s", results_file_path)
                for (
                    reproducer,
                    saved_issue_title,
                    binary_path,
                    bug_sample,
                    run_args,
                    run_env,
                ) in saved_bugs_iter(
                    results_file_path,
                    mask,
                    restore_app_config,
                    reproducers_cache=reproducers_cache,
                ):
                    log.debug("found bug sample: %s", bug_sample)

                    # do not re-run same issue multiple times, just mark as old
                    if saved_issue_title in self.issue_cards:
                        self.issue_cards[saved_issue_title].is_old = True
                        log.verbose3(
                            "Not trying old bug, as it has already been reproduced: %s",
                            bug_sample,
                        )
                        continue

                    crashes, hangs = sample_path_to_crash_hang_tuple(bug_sample)

                    if run_args is not None and run_env is not None:
                        reproducer.set_run_args(shlex.split(run_args))
                        reproducer.set_run_env(run_env)
                    else:
                        reproducer.set_run_args(self.app_config.run_args or [])
                        reproducer.set_run_env(self.app_config.run_env)

                    issue_cards = reproducer.run_binary_on_samples(
                        binary_path,
                        crashes,
                        hangs,
                        self.reproduce_settings.hang_reproduce_limit,
                    )
                    for card in issue_cards:
                        log.warning(
                            "Old bug is still reproducible. Binary: %s, sample: %s",
                            binary_path,
                            bug_sample,
                        )
                        card.is_old = True

                    if len(issue_cards) > 0:
                        self.add_reproduce_issue_cards(issue_cards)
                    else:
                        log.verbose1(
                            "Old bug is not reproducible (possibly fixed): %s",
                            saved_issue_title,
                        )

    def reproduce_extra_bugs(self, sample_masks: Optional[Sequence[str]]) -> None:
        """
        Reproduce bugs matching `sample_masks`, discovered by other fuzzers (not controlled by bugbane).
        The "bb_results.json" files are not searched for.
        """

        if not sample_masks:
            return

        if not self.app_config.specs and not self.app_config.run_args:
            log.warning(
                "Can't reproduce extra bugs without specs (app config) or program with its run args. Skipping..."
            )
            return

        log.info(
            "Reproducing EXTRA bugs outside fuzzer sync dir, sample masks: %s",
            ", ".join(sample_masks),
        )

        specs_to_use = self.app_config.specs
        run_args_to_use = self.app_config.run_args

        if not specs_to_use:
            if not self.app_config.run_args:
                log.warning(
                    "Can't reproduce extra bugs without specs: program with its run args required. Skipping..."
                )
                return

            # manual mode without --spec: create a fake spec from run args
            # XXX: there will be problems with go-fuzz, and we can't check it here

            binary = self.app_config.run_args[0]
            if not os.path.isfile(binary):
                log.warning(
                    "Can't reproduce extra bugs without specs: program does not exist: %s. Skipping...",
                    binary,
                )
                return

            specs_to_use = [["AFL++:out", self.app_config.run_args[0] + ":dummy"]]
            run_args_to_use = self.app_config.run_args[1:]

        for fuzzer_dir_and_builds in specs_to_use:
            spec_name = " ".join(fuzzer_dir_and_builds)
            log.verbose1("Checking spec '%s'...", spec_name)

            fuzzer_and_syncdir = fuzzer_dir_and_builds[0]
            fuzzer_type, _ = fuzzer_and_syncdir.split(":", 1)

            build_specs = fuzzer_dir_and_builds[1:]

            reproducer = ReproducerFactory.create(fuzzer_type)
            reproducer.set_run_args(run_args_to_use or [])
            reproducer.set_run_env(self.app_config.run_env)

            for build_spec in build_specs:
                binary_path, _ = build_spec.split(":")
                for one_sample_mask in sample_masks:
                    for bug_sample_path in glob.iglob(one_sample_mask):
                        crashes, hangs = sample_path_to_crash_hang_tuple(
                            bug_sample_path
                        )
                        issue_cards = reproducer.run_binary_on_samples(
                            binary_path,
                            crashes,
                            hangs,
                            self.reproduce_settings.hang_reproduce_limit,
                        )
                        for card in issue_cards:
                            card.is_extra = True
                        self.add_reproduce_issue_cards(issue_cards)


def saved_bugs_iter(
    results_file_path: str,
    sample_mask: str,
    restore_app_config: bool,
    reproducers_cache: Dict[str, Reproducer],
) -> Iterable[
    Tuple[Reproducer, str, str, str, Optional[str], Optional[Dict[str, str]]]
]:
    """
    This method iterates over saved bugs corresponding to given `results_file_path`
    and filtered by `sample_mask`.
    Yields tuples: (reproducer, issue_title, binary_path, sample_path [, run_args, run_env])
    """
    try:
        data = load_dict_from_json_file(results_file_path)
    except FileUtilsException as e:
        raise HarvesterError(
            f"while trying to load contents from file {results_file_path}: {e}"
        ) from e

    issues = data.get("issue_cards")
    if not issues:
        return

    samples_dir = samples_dir_for_results_file(results_file_path, sample_mask)

    log.debug("samples_dir=%s", samples_dir)

    for issue in issues:
        repr_cmd = issue.get("reproduce_cmd", "")
        log.debug("repr_cmd=%s", repr_cmd)

        try:
            repr_name = ReproducerFactory.get_reproducer_name_from_reproduce_cmd(
                repr_cmd
            )
            if repr_name not in reproducers_cache:
                reproducer = ReproducerFactory.create(repr_name)
                reproducers_cache[repr_name] = reproducer
                if not reproducer.can_run_tested_app():
                    log.warning(
                        "Reproducer %s CAN'T re-run bugs, as it's not able to run tested app",
                        reproducer.__class__.__name__,
                    )
                    continue
        except TypeError:
            log.warning(
                "can't determine reproducer for reproduce command %s (skipping!)",
                repr_cmd,
            )
            continue

        reproducer = reproducers_cache[repr_name]
        log.debug("reproducer=%s", reproducer)

        binary = issue.get("binary")

        # skip samples which couldn't be reproduced by running tested binary
        if repr_cmd.startswith("cat ") and binary != "cat":
            continue

        if not os.path.isfile(binary):
            continue

        sample = issue.get("sample")
        sample_path = os.path.join(samples_dir, sample)
        log.debug("isfile('%s') = %r", sample_path, os.path.isfile(sample_path))
        if not os.path.isfile(sample_path):
            continue

        if not fnmatch.fnmatch(sample_path, sample_mask):
            continue

        run_args: Optional[str] = None
        run_env: Optional[Dict[str, str]] = None

        title = issue.get("title", sample)

        if restore_app_config:

            try:
                run_args = restore_run_args(repr_cmd)
            except HarvesterError:
                log.warning("wasn't able to restore run args from old bug '%s'", title)
                continue

            try:
                run_env = make_env_dict_from_str(issue.get("reproduce_env"))
            except ProcessException:
                log.warning(
                    "wasn't able to parse reproduce env from old bug '%s'", title
                )
                continue

        yield reproducer, title, binary, sample_path, run_args, run_env


def samples_dir_for_results_file(results_file_path: str, bug_samples_mask: str) -> str:
    """
    Given a path to bugbane results file (such as "bb_results.json") `results_file_path`,
    and a user provided mask to find bug samples `bug_samples_mask`
    return samples directory corresponding to the results file.
    """
    log.debug(
        "results_file_path=%s, bug_samples_mask=%s", results_file_path, bug_samples_mask
    )
    path_parts = os.path.normpath(results_file_path).split(os.sep)
    mask_parts = os.path.normpath(bug_samples_mask).split(os.sep)

    path_parts[-1] = "*"

    parts: List[str] = []
    for i, (path_part, mask_part) in enumerate(zip(path_parts, mask_parts)):
        if not fnmatch.fnmatch(path_part, mask_part):
            parts.extend(mask_parts[i:])
            break
        parts.append(path_part)

    if parts[-1] == "*":
        del parts[-1]
    res = os.path.normpath(os.path.join(*parts))

    if results_file_path[0] == os.sep:
        return os.sep + res
    return res


def restore_run_args(reproduce_cmd: str) -> str:
    """
    For `reproduce_cmd` containing a specific sample path
    (such as `ubsan/app --file "./out/target/crashes/id:000000,sig:06,sync:m1,src:000000"`)
    return generic run args (such as `--file @@`)
    """
    parts = shlex.split(reproduce_cmd)

    # detect gdb reproduce command, extract its "run" option
    if "gdb" in parts and "--ex" in parts:
        for arg in parts:
            if arg.startswith("r ") or arg.startswith("run "):
                parts = shlex.split(arg)
                break

    if "<" in parts:
        parts = parts[: parts.index("<")]
    else:
        file_idx = detect_sample_arg(parts)
        if file_idx is None:
            raise HarvesterError(
                f"wasn't able to restore run args from reproduce_cmd={reproduce_cmd}"
            )

        parts[file_idx] = "@@"

    # shlex.join as in newer pythons
    return " ".join(shlex.quote(arg) for arg in parts[1:])


def detect_sample_arg(args: Sequence[str]) -> Optional[int]:
    """
    Try to detect argument containing sample path.
    Return index of that argument in the `args` sequence.
    Return None if no such argument was detected.
    """

    patterns = {
        "crashes/id": 2,
        "hangs/id": 2,
        "artifacts/": 2,
        "out/": 1,
    }
    scores = [0] * len(args)
    for i, arg in enumerate(args):
        for pat, score in patterns.items():
            if pat in arg:
                scores[i] += score

    scores[0] = 0

    if len(scores) == 2 and scores[1] > 0:
        return 1

    for i, arg in enumerate(args):
        if "/" in arg:
            scores[i] += 1

    scores[0] = 0

    if len(scores) == 2 and scores[1] > 0:
        return 1

    max_score = max(scores)
    if max_score == 0:
        return None

    if scores.count(max_score) > 1:
        return None

    return scores.index(max_score, 1)


def sample_path_to_crash_hang_tuple(
    bug_sample_path: str,
) -> Union[Tuple[Tuple[()], Tuple[str]], Tuple[Tuple[str], Tuple[()]]]:
    """
    Based on `bug_sample_path` returns
    EITHER (), (bug_sample_name,) if it looks like a hang,
    OR (bug_sample_name,), () if it doesn't look like a hang.
    """

    hang_start_patterns = ("hang", "timeout-")
    if any(
        os.path.basename(bug_sample_path).lower().startswith(pat)
        for pat in hang_start_patterns
    ):
        return ((), (bug_sample_path,))

    if os.path.join("hangs", "id") in bug_sample_path:
        return ((), (bug_sample_path,))

    return ((bug_sample_path,), ())
