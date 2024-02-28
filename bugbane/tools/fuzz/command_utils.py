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

from typing import List, Optional, Dict
from bugbane.modules.process import run_interactive_shell_cmd


class CmdUtilsException(Exception):
    """Exception class for errors in command utils module."""


def make_tmux_commands(
    all_cmds: Dict[str, int],
    create_session: bool = True,
    tmux_socket_name: Optional[str] = None,
    tmux_session_name: Optional[str] = None,
) -> List[str]:
    """
    Convert list of commands to tmux commands.
    all_cmds: dict mapping commands to be run in tmux to their wanted window indexes.
    If window index is already in use, it will be destroyed by tmux (new-window -k ...)
    """
    tmux_socket_name = tmux_socket_name or "fuzz"
    tmux_session_name = tmux_session_name or "fuzz"

    cmds: List[str] = []

    if create_session:
        cmds.append(
            f'tmux -L "{tmux_socket_name}" new-session -d -x 90 -y 35 -s "{tmux_session_name}"'
        )

    for cmd, i in all_cmds.items():
        window_name = f"{tmux_session_name}-{i}"
        cmds.append(
            f'tmux -L "{tmux_socket_name}" new-window -k -dn "{window_name}" -t {i} \'{cmd} ; sh -i\''
        )

    return cmds


def get_tmux_server_pid(tmux_socket_name: str) -> int:
    """Return tmux server process id by the given tmux socket name."""
    exit_code, output = run_interactive_shell_cmd(
        f"tmux -L \"{tmux_socket_name}\" list-sessions -F '#{{pid}}'"
    )
    try:
        if exit_code != 0:
            raise RuntimeError()
        return int(output.decode("utf-8"))
    except (RuntimeError, ValueError, UnicodeDecodeError):
        raise CmdUtilsException("wasn't able to determine tmux server pid")
