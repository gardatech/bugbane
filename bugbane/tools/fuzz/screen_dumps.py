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

from typing import Optional, List

import os
import logging

log = logging.getLogger(__name__)

from bugbane.modules.fuzzer_cmd.fuzzer_cmd import FuzzerCmd
from bugbane.modules.process import run_interactive_shell_cmd


def make_tmux_screen_dumps(
    fuzz_cmd_generator: FuzzerCmd,
    num_fuzz_instances: int,
    have_stats_instance: bool,
    screens_dir: str,
):
    """
    Creates list of tmux commands using provided fuzz cmd generator.
    Makes screen dumps and saves them to screens_dir.
    """

    log.verbose1("Saving tmux screen dumps to %s...", screens_dir)

    os.makedirs(screens_dir, exist_ok=True)

    screen_dump_cmds = fuzz_cmd_generator.make_tmux_screen_capture_cmds(
        num_fuzz_instances, have_stats_instance
    )
    ok_screens = 0
    for i, screen_dump_cmd in enumerate(screen_dump_cmds, start=1):
        screen_file_path = os.path.join(screens_dir, "screen" + str(i))
        log.verbose3("Dumping screen #%d to %s", i, screen_file_path)
        exit_code, output = run_interactive_shell_cmd(screen_dump_cmd)
        if exit_code != 0:
            log.error("Wasn't able to dump tmux screen #%d (bad cmd exit code)", i)
            continue

        try:
            with open(screen_file_path, "wb") as f:
                f.write(output)
        except OSError as e:
            log.error(
                "Wasn't able to dump tmux screen to %s (OSError: %s)",
                screen_file_path,
                e,
            )
        ok_screens += 1
    log.verbose2("Saved %d screen dumps to %s", ok_screens, screens_dir)
