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

from typing import List, Optional


def make_tmux_commands(
    all_cmds: List[str], tmux_session_name: Optional[str] = None
) -> List[str]:
    """
    Convert list of commands to tmux commands.
    all_cmds: list of commands that need to be run via tmux
    """
    tmux_session_name = tmux_session_name or "fuzz"

    cmds = []

    cmds.append(f"tmux new-session -d -x 90 -y 35 -s {tmux_session_name}")
    for i, cmd in enumerate(all_cmds, start=1):
        if cmd is None:
            continue

        cmds.append(f"tmux new-window -dn {tmux_session_name}:{i} '{cmd}'")

    return cmds
