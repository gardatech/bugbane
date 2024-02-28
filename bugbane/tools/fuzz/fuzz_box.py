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

from typing import Optional, List, Any, Dict

import os
import signal
import psutil
from copy import deepcopy
from time import sleep, time

# TODO: refactor methods of FuzzBox
# TODO: check if disk space is OK
# TODO: calculate progress towards stop condition goal

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.process import (
    run_interactive_shell_cmd,
    get_process_children,
    ProcessException,
)
from bugbane.modules.corpus_utils import ensure_initial_corpus_exists
from bugbane.modules.format_utils import seconds_to_hms

from bugbane.modules.fuzz_data_suite import FuzzDataSuite
from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats, FuzzStatsError
from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo
from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_cmd.fuzzer_cmd import FuzzerCmd, FuzzerCmdError
from bugbane.modules.fuzzer_cmd.factory import FuzzerCmdFactory

from .stop_conditions import (
    StopConditions,
    StopConditionError,
    detect_required_stop_condition,
)

from .dict_utils import merge_dictionaries_to_file, DictMergeError
from .command_utils import make_tmux_commands, get_tmux_server_pid, CmdUtilsException
from .screen_dumps import make_tmux_screen_dumps
from .fuzz_config import FuzzConfig


def limit_cpu_cores(from_config: Optional[int], max_from_args: int) -> int:
    """
    Limit number of cpu cores used for fuzzing based on:
        1. value from config file in self.fuzz_config.fuzz_cores ("developer provided value")
        2. value from run argument --max-cpus in max_cpus_argument ("AppSec provided limit")
        3. os.cpu_count value (hardware limit)
    """
    fuzz_cores = from_config or 8
    max_cpus = min(max_from_args, os.cpu_count() or 1)
    return min(fuzz_cores, max_cpus)


class FuzzBoxError(Exception):
    """Exception class for errors in the `FuzzBox` class."""


class CannotContinueFuzzingException(FuzzBoxError):
    """
    Fuzzing process cannot continue.
    E.g., `go test` has found a bug and exited.
    """


class FuzzBox:
    """
    Class for controlling fuzzing process:
        1. Starting
        2. Running until stop condition
    """

    def __init__(self, fuzz_config: FuzzConfig, suite_dir: str, suite: FuzzDataSuite):
        fuzzer_type = fuzz_config.fuzzer_type
        try:
            cmdgen: FuzzerCmd = FuzzerCmdFactory.create(fuzzer_type)
            stats: FuzzStats = FuzzStatsFactory.create(fuzzer_type)
            info: FuzzerInfo = FuzzerInfoFactory.create(fuzzer_type)
        except TypeError as e:
            log.error(
                "Wasn't able to create command generator and/or fuzz stats of type '%s'",
                fuzzer_type,
            )
            raise FuzzBoxError("can't create fuzzer") from e

        log.verbose1("Using %s fuzz command generator", cmdgen.__class__.__name__)
        log.verbose1("Using %s stats", stats.__class__.__name__)
        log.verbose1("Using %s fuzzer paths", info.__class__.__name__)

        self.cmdgen = cmdgen
        self.stats = stats
        self.info = info
        self.fuzz_config = fuzz_config
        self.suite_dir = suite_dir
        self.suite = suite
        self.fuzz_sync_dir = os.path.join(suite_dir, "out")

        self.tmux_server_pid = -1
        self.num_cmd_restarts: Dict[str, int] = {}
        self.start_interval_seconds = 0
        self.fuzz_cmds: Dict[str, int] = {}

    def start(self, start_interval_ms: int, max_cpus_argument: int):
        in_dir = self.info.input_dir(self.fuzz_sync_dir)
        self._prepare_input_corpus_dir(in_dir)
        dict_path = self._merge_dicts()
        self.start_interval_seconds = start_interval_ms / 1000.0

        self._limit_cpu_cores(max_cpus_argument)
        self._run_fuzzers(
            in_dir=in_dir,
            dict_path=dict_path,
        )
        self._init_stop_condition()
        self.start_timestamp = int(time())

    def _limit_cpu_cores(self, max_cpus_argument: int):
        from_config = self.fuzz_config.fuzz_cores

        fuzz_cores = limit_cpu_cores(
            from_config=from_config, max_from_args=max_cpus_argument
        )

        if from_config is not None and from_config < fuzz_cores:
            log.warning("limiting number of CPU cores to %d", fuzz_cores)

        self.fuzz_config.fuzz_cores = fuzz_cores

    def _merge_dicts(self):
        """Merge input dictionaries, return path to merged dictionary."""

        wanted_dict_path = os.path.join(self.suite_dir, "merged.dict")
        try:
            dict_path = merge_dictionaries_to_file(
                self.suite.dicts_dir, wanted_dict_path
            )
        except DictMergeError as e:
            raise FuzzBoxError(f"wasn't able to prepare dictionary file: {e}") from e
        return dict_path

    def _prepare_input_corpus_dir(self, in_dir: str):
        if self.info.initial_samples_required():
            ensure_initial_corpus_exists(in_dir)

    def _run_fuzzers(
        self,
        in_dir: str,
        dict_path: Optional[str],
    ) -> None:
        fuzz_config = self.fuzz_config
        log.info("[*] Using %d cores for fuzzing", fuzz_config.fuzz_cores)
        try:
            fuzz_cmds, reproduce_specs = self.cmdgen.generate(
                run_args=fuzz_config.run_args,
                run_env=fuzz_config.run_env,
                count=fuzz_config.fuzz_cores,
                builds=fuzz_config.builds,
                timeout_ms=fuzz_config.timeout,
                input_corpus=in_dir,
                output_corpus=self.fuzz_sync_dir,
                dict_path=dict_path,
            )
        except (FuzzerCmdError, IndexError) as e:
            raise FuzzBoxError(f"wasn't able to create fuzz commands: {e}") from e

        self.reproduce_specs = reproduce_specs

        all_cmds: List[str] = []
        stats_cmd = self.cmdgen.stats_cmd(self.fuzz_sync_dir)
        if stats_cmd is not None:
            all_cmds.append(stats_cmd)

        fuzz_cmds = [cmd.strip() for cmd in fuzz_cmds]
        all_cmds.extend(fuzz_cmds)

        self.fuzz_cmds = {cmd: i for i, cmd in enumerate(all_cmds, start=1)}

        log.info(
            "[*] Using the following commands:\n\t%s",
            "\n\t".join(cmd for cmd in all_cmds if cmd is not None),
        )

        with open(os.path.join(self.suite_dir, "fuzz.cmds"), "wt") as f:
            print("\n".join(cmd for cmd in all_cmds if cmd is not None), file=f)

        self.run_fuzzer_cmds(fuzzer_cmds=self.fuzz_cmds, initial_run=True)

        # commands to be monitored and restarted

        try:
            self.tmux_server_pid = get_tmux_server_pid(
                self.fuzz_config.tmux_socket_name
            )
        except CmdUtilsException as e:
            raise FuzzBoxError("tmux process not found") from e

        for cmd in self.fuzz_cmds:
            self.num_cmd_restarts[cmd] = 0

    def run_fuzzer_cmds(
        self, fuzzer_cmds: Dict[str, int], initial_run: bool = False
    ) -> None:
        tmux_cmds = make_tmux_commands(
            fuzzer_cmds,
            create_session=initial_run,
            tmux_socket_name=self.fuzz_config.tmux_socket_name,
            tmux_session_name=self.fuzz_config.tmux_session_name,
        )

        log.verbose2(
            "[*] Running the following TMUX commands:\n\t%s",
            "\n\t".join(tmux_cmds),
        )
        extra_env = {
            "AFL_PIZZA_MODE": "0",  # disable AFL++ 1st april joke
        }

        for tmux_cmd in tmux_cmds:
            # all the tmux commands actually use -d arg (detached mode)
            exit_code, output = run_interactive_shell_cmd(tmux_cmd, extra_env=extra_env)
            if exit_code != 0:
                output = output.decode("utf-8", errors="replace")
                raise FuzzBoxError(
                    f"failed to run command '{tmux_cmd}'. Output follows:\n{output}"
                )

            if self.start_interval_seconds > 0.0:
                sleep(self.start_interval_seconds)

    def check_and_restart_fuzzers(self) -> None:
        """
        Check whether the fuzzers are still running.
        Try restarting them.
        """

        try:
            children_procs = get_process_children(self.tmux_server_pid, recursive=True)
        except ProcessException as e:
            raise FuzzBoxError("tmux process not found") from e

        cmds_found: List[str] = []
        cmds_to_restart: List[str] = []

        try_restart_times = 3

        for proc in children_procs:
            if not proc.is_running():
                continue

            try:
                cmdline = " ".join(proc.cmdline())
            except psutil.Error:
                continue

            for expected_cmd in self.fuzz_cmds:
                if expected_cmd is None:
                    continue

                if expected_cmd in cmds_found:
                    continue

                if expected_cmd.startswith(cmdline):
                    log.trace("Fuzzer cmd is still running: %s", expected_cmd)
                    cmds_found.append(expected_cmd)
                    break

        for expected_cmd in self.fuzz_cmds:
            if expected_cmd is None:
                continue

            if expected_cmd in cmds_found:
                continue

            # cmd is not running anymore - need to do something

            if self.num_cmd_restarts[expected_cmd] > try_restart_times:
                continue

            self.num_cmd_restarts[expected_cmd] += 1
            if self.num_cmd_restarts[expected_cmd] > try_restart_times:
                log.warning("GAVE UP on restarting the fuzzer cmd: %s", expected_cmd)
                continue

            log.warning("RESTARTING fuzzer cmd: %s", expected_cmd)
            cmds_to_restart.append(expected_cmd)

        bad_fuzzing = False
        if len(cmds_found) < 2 and len(cmds_to_restart) == 0:
            if len(cmds_found) == 1:
                stats_cmd = self.cmdgen.stats_cmd(self.fuzz_sync_dir)
                if stats_cmd is not None and stats_cmd in cmds_found:
                    bad_fuzzing = True
            else:  # empty cmds_found
                bad_fuzzing = True

        if bad_fuzzing:
            log.error(
                "fuzzers don't work. Please check manually by running one of the following commands:\n%s",
                "\n".join(self.fuzz_cmds),
            )
            raise FuzzBoxError("fuzzers don't work. Please check manually")

        if len(cmds_to_restart) < 1:
            return

        cmds_dict = {k: self.fuzz_cmds[k] for k in cmds_to_restart}
        self.run_fuzzer_cmds(fuzzer_cmds=cmds_dict)

    def _init_stop_condition(self) -> None:
        try:
            stop_cond_name, required_duration = detect_required_stop_condition(
                environ=os.environ.copy()
            )
        except StopConditionError as e:
            raise FuzzBoxError(f"failed to detect required stop condition: {e}") from e

        if stop_cond_name == "time_without_finds":
            stop_conditions = {"minutes_without_paths": required_duration // 60}
        else:  # real_run_time
            stop_conditions = {"minutes_run_time": required_duration // 60}

        log.info(
            "[*] STOP CONDITION: %s = %d seconds", stop_cond_name, required_duration
        )

        self.stop_cond_name = stop_cond_name
        self.required_duration = required_duration
        self.stop_conditions = stop_conditions

    def wait_until_stop_condition(self) -> None:
        """
        Fuzzing loop:
            1. Print current fuzz stats
            2. Check for stop condition
        """
        sleep(5.0)

        self._display_process_tree()

        stats_print_counter = 0
        self.real_duration = 0

        stop_cond_met = False
        while not stop_cond_met:
            stop_cond_met = self._wait_loop_iteration(stats_counter=stats_print_counter)
            stats_print_counter = (stats_print_counter + 1) % 6

        log.info(
            "Stop condition '%s = %d seconds' met!",
            self.stop_cond_name,
            self.required_duration,
        )

    def _display_process_tree(self):
        """
        Prints out pstree output if the tool is available.
        """
        exit_code, output = run_interactive_shell_cmd("pstree -a | grep -v pstree")
        if exit_code == 0 and output:
            log.info("Fuzz process tree:\n%s", output.decode(errors="replace"))

    def _wait_loop_iteration(self, stats_counter: int) -> bool:
        """
        One iteration of fuzzing loop.
        Return True if stop condition was met.
        """

        sleep(10.0)

        self.check_and_restart_fuzzers()

        real_duration = int(time()) - self.start_timestamp

        stats_dir = self.info.stats_dir(self.fuzz_sync_dir)

        try:
            self.stats.load(stats_dir)
            if stats_counter == 0:
                log.info("[%s] %s", seconds_to_hms(real_duration), self.stats)
            if (
                self.stats.crashes > 0 or self.stats.hangs > 0
            ) and not self.info.can_continue_after_bug():
                raise CannotContinueFuzzingException(
                    "a bug was found and selected fuzzer cannot continue testing"
                )
        except FileNotFoundError:
            log.debug("FileNotFoundError when trying to load stats")
            return False

        return StopConditions.met(
            self.stop_cond_name, self.stats, self.required_duration
        )

    def stop_and_update_vars(
        self, bane_vars: Dict[str, Any], interrupted: bool
    ) -> None:
        real_duration = int(time()) - self.start_timestamp
        last_fuzz_stats = deepcopy(self.stats)
        stats_dir = self.info.stats_dir(self.fuzz_sync_dir)
        try:
            self.stats.load(stats_dir)
        except FileNotFoundError:
            self.stats = last_fuzz_stats
        log.info("[%s] %s", seconds_to_hms(real_duration), self.stats)

        self._dump_screens()
        self._kill_fuzzers()

        fuzz_time_real_seconds = real_duration

        stop_conditions = {} if interrupted else self.stop_conditions

        self.fuzz_config.update_config_vars(
            config_vars=bane_vars,
            fuzz_sync_dir=self.fuzz_sync_dir,
            stop_conditions=stop_conditions,
            fuzz_time_real_seconds=fuzz_time_real_seconds,
            reproduce_specs=self.reproduce_specs,
        )

    def _dump_screens(self) -> None:
        """
        Dump tmux panes on disk.
        """
        log.verbose1("Dumping screens...")
        screens_dir = os.path.join(self.suite_dir, "screens")

        make_tmux_screen_dumps(
            fuzz_cmd_generator=self.cmdgen,
            num_fuzz_instances=len(self.fuzz_cmds),
            screens_dir=screens_dir,
        )

    def _kill_fuzzers(self) -> None:
        """
        Stop fuzzers and tmux which we previously spawned.
        """
        log.verbose1("Stopping fuzzers and tmux...")

        try:
            procs = get_process_children(self.tmux_server_pid, recursive=True)
        except ProcessException:
            return

        fuzzer_procs = []

        for p in procs:
            if not p.is_running():
                continue

            try:
                cmdline = " ".join(p.cmdline())
            except psutil.Error:
                continue

            for cmd in self.fuzz_cmds:
                if cmd.startswith(cmdline):
                    fuzzer_procs.append(p)
                    break

        for p in fuzzer_procs:
            if p.is_running():
                p.send_signal(signal.SIGINT)
        sleep(2.0)

        for p in fuzzer_procs:
            if p.is_running():
                p.send_signal(signal.SIGKILL)
        sleep(1.0)

        try:
            tmux_proc = psutil.Process(self.tmux_server_pid)
            if tmux_proc.is_running():
                tmux_proc.send_signal(signal.SIGTERM)
        except psutil.Error:
            return
