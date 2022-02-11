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
import sys
import shutil
from copy import deepcopy
from time import sleep, time

# TODO: REFACTOR MAIN
# TODO: check if fuzzers are still running -> restart them or stop fuzzing job
# TODO: check if disk space is OK
# TODO: calculate progress towards stop condition goal

from bugbane.modules.log import get_first_logger
from bugbane.modules.process import run_interactive_shell_cmd
from bugbane.modules.corpus_utils import ensure_initial_corpus_exists
from bugbane.modules.format import seconds_to_hms

from bugbane.modules.builds import BuildDetectionError, get_builds
from bugbane.modules.fuzz_data_suite import FuzzDataSuite, FuzzDataError
from bugbane.modules.stats.fuzz.fuzz_stats import FuzzStats, FuzzStatsError
from bugbane.modules.stats.fuzz.factory import FuzzStatsFactory
from bugbane.modules.fuzzer_info.fuzzer_info import FuzzerInfo
from bugbane.modules.fuzzer_info.factory import FuzzerInfoFactory
from bugbane.modules.fuzzer_cmd.fuzzer_cmd import FuzzerCmd
from bugbane.modules.fuzzer_cmd.factory import FuzzerCmdFactory

from .args import parse_args
from .stop_conditions import (
    StopConditions,
    StopConditionError,
    detect_required_stop_condition,
)

from .command_utils import make_tmux_commands
from .screen_dumps import make_tmux_screen_dumps


def main(argv=None):
    """
    1. Load tested app information, fuzzer_type, fuzz_cores from bane_vars file
    2. Generate fuzz & tmux commands
    3. Fuzz until stop condition reached
    4. Print stats & progress
    5. Update bane_vars file (fuzzer_version, fuzz_cores, used sanitizers)
    """

    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_first_logger(__name__, args.verbose)

    if shutil.which("tmux") is None:
        log.error("tmux not found in PATH")
        return 1

    try:
        suite, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.suite)
    except FuzzDataError as e:
        log.error("Wasn't able to load fuzzing suite paths: %s", e)
        return 1
    log.verbose1("Loaded fuzzing suite: %s", suite)

    tested_binary_path = bane_vars.get("tested_binary_path")
    if tested_binary_path is None:
        log.error("tested_binary_path field missing in vars file")
        return 1

    try:
        builds = get_builds(args.suite, tested_binary_path)
    except BuildDetectionError as e:
        log.error("Bad fuzzing suite: %s", e)
        return 1

    log.info("Have %d builds", len(builds))
    bane_vars["sanitizers"] = [
        bt.name for bt, _ in builds.items() if bt.is_static_sanitizer()
    ]

    max_cpus = min(args.max_cpus, os.cpu_count())
    fuzz_cores = bane_vars.get("fuzz_cores") or 8
    if fuzz_cores > max_cpus:
        log.warning("limiting number of CPU cores to %d", max_cpus)
        fuzz_cores = max_cpus
    bane_vars["fuzz_cores"] = fuzz_cores

    log.info("[*] Using %d cores for fuzzing", fuzz_cores)

    src_root = bane_vars.get("src_root")
    if not src_root:
        log.error(
            "src_root variable not found in configuration file, won't be able to collect coverage"
        )
        return 1

    try:
        fuzzer_type = bane_vars["fuzzer_type"]
    except KeyError:
        log.error("fuzzer_type variable not found in configuration file")
        return 1

    try:
        cmdgen: FuzzerCmd = FuzzerCmdFactory.create(fuzzer_type)
        log.verbose1("Using %s fuzz command generator", cmdgen.__class__.__name__)
        fuzz_stats: FuzzStats = FuzzStatsFactory.create(fuzzer_type)
        log.verbose1("Using %s stats", fuzz_stats.__class__.__name__)
        fuzzer_info: FuzzerInfo = FuzzerInfoFactory.create(fuzzer_type)
        log.verbose1("Using %s fuzzer paths", fuzzer_info.__class__.__name__)
    except TypeError:
        log.error(
            "Wasn't able to create command generator and/or fuzz stats of type '%s'",
            fuzzer_type,
        )
        return 1

    out_dir = os.path.join(args.suite, "out")
    bane_vars["fuzz_sync_dir"] = out_dir

    in_dir = fuzzer_info.input_dir(out_dir)
    if fuzzer_info.initial_samples_required():
        ensure_initial_corpus_exists(in_dir)

    # TODO: respect run_env from bane_vars file
    run_args = bane_vars.get("run_args") or ""
    bane_vars["run_args"] = run_args  # ensure saved run_args var is not null

    app = bane_vars.get("tested_binary_path") or "./a.out"
    app_name = os.path.basename(app)
    bane_vars["tested_binary_name"] = app_name

    try:
        fuzz_cmds, reproduce_specs = cmdgen.generate(
            run_args=run_args,
            input_corpus=in_dir,
            output_corpus=out_dir,
            count=fuzz_cores,
            builds=builds,
        )
    except (ArithmeticError, IndexError) as e:
        log.error("wasn't able to create fuzz commands: %s", e)
        return 1
    bane_vars["reproduce_specs"] = reproduce_specs

    stats_cmd = cmdgen.stats_cmd(out_dir)
    stats_dir = fuzzer_info.stats_dir(out_dir)

    fuzz_cmds = [cmd.strip() for cmd in fuzz_cmds]
    all_cmds = [stats_cmd] + fuzz_cmds

    log.info(
        "[*] Using the following commands:\n\t%s",
        "\n\t".join(cmd for cmd in all_cmds if cmd is not None),
    )

    with open(os.path.join(args.suite, "fuzz.cmds"), "wt") as f:
        print("\n".join(cmd for cmd in all_cmds if cmd is not None), file=f)

    try:
        stop_cond_name, duration = detect_required_stop_condition(
            environ=os.environ, bane_vars=bane_vars
        )
    except StopConditionError as e:
        log.error(e)
        return 1

    if stop_cond_name == "time_without_finds":
        bane_vars["stop_conditions"] = {"minutes_without_paths": duration // 60}
    else:  # real_run_time
        bane_vars["stop_conditions"] = {"minutes_run_time": duration // 60}

    log.info("[*] STOP CONDITION: %s = %d seconds", stop_cond_name, duration)

    tmux_cmds = make_tmux_commands(all_cmds)
    log.verbose2(
        "[*] Running the following TMUX commands:\n\t%s",
        "\n\t".join(tmux_cmds),
    )

    for tmux_cmd in tmux_cmds:
        # all the tmux commands actually use -d arg (detached mode)
        exit_code, output = run_interactive_shell_cmd(tmux_cmd)
        if exit_code != 0:
            log.error(
                "Wasn't able to run command: %s. Output follows:\n%s", tmux_cmd, output
            )
            return 1

    try:
        sleep(5.0)

        exit_code, output = run_interactive_shell_cmd("pstree -a | grep -v pstree")
        if exit_code == 0 and output:
            log.info("Fuzz process tree:\n%s", output.decode(errors="replace"))

        start_timestamp = int(time())
        stats_print_counter = 0
        real_duration = 0

        while True:
            sleep(10.0)
            real_duration = int(time()) - start_timestamp

            try:
                fuzz_stats.load(stats_dir)

                stats_print_counter = (stats_print_counter + 1) % 6
                if stats_print_counter == 0:
                    log.info("[%s] %s", seconds_to_hms(real_duration), fuzz_stats)

            except FileNotFoundError:
                log.debug("FileNotFoundError when trying to load stats")
            else:
                if StopConditions.met(stop_cond_name, fuzz_stats, duration):
                    log.info(
                        "Stop condition '%s = %d seconds' met!",
                        stop_cond_name,
                        duration,
                    )
                    break

    except KeyboardInterrupt:
        log.info("")
        log.info("[!] Fuzzing stopped by signal SIGINT")
        bane_vars["stop_conditions"] = {}

    real_duration = int(time()) - start_timestamp
    last_fuzz_stats = deepcopy(fuzz_stats)
    try:
        fuzz_stats.load(stats_dir)
    except FileNotFoundError:
        fuzz_stats = last_fuzz_stats
    log.info("[%s] %s", seconds_to_hms(real_duration), fuzz_stats)

    log.verbose1("Dumping screens...")
    screens_dir = os.path.join(args.suite, "screens")

    make_tmux_screen_dumps(
        fuzz_cmd_generator=cmdgen,
        num_fuzz_instances=len(fuzz_cmds),
        have_stats_instance=stats_cmd is not None,
        screens_dir=screens_dir,
    )

    log.verbose1("Stopping fuzzers and tmux...")
    run_interactive_shell_cmd(  # TODO: kill fuzz target binaries (cmplog leftovers etc)
        """killall -q -s SIGINT afl-fuzz; \
        sleep 2s; \
        killall -q -s SIGKILL afl-fuzz; \
        killall -q 'tmux: server' tmux; \
        sleep 1s; \
        killall -q -s SIGKILL 'tmux: server' tmux"""
    )

    log.info("[+] Fuzzing complete, updating configuration file")
    bane_vars["fuzz_time_real_seconds"] = real_duration
    suite.save_vars(bane_vars)

    return 0
