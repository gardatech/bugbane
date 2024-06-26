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

from typing import Tuple, List, Dict, Optional

import os
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired, SubprocessError
import shlex

import psutil

from bugbane.modules.log import getLogger

log = getLogger(__name__)


class ProcessException(Exception):
    """Exception class for errors in the process module."""


def checked_run_shell_cmd(
    cmd: str, extra_env: Optional[Dict[str, str]] = None, timeout_sec: int = 120
) -> bool:
    """
    Return True if run was successfull
    """
    log.verbose2("Running %s...", cmd)
    exit_code, is_timeout, output = run_shell_cmd(cmd, extra_env, timeout_sec)
    err_part = ""
    if exit_code == 0:
        return True

    if is_timeout:
        err_part = f"Timeout (cmd took more than {timeout_sec} seconds to run)"
    else:
        output = output.decode(errors="replace")
        err_part = f"Bad exit code {exit_code}"

    log.error(
        "Running of cmd '%s' failed: %s. Output follows:\n%s",
        cmd,
        err_part,
        output,
    )
    return False


def run_shell_cmd(
    cmd: str, extra_env: Optional[Dict[str, str]] = None, timeout_sec: int = 120
) -> Tuple[Optional[int], bool, Optional[bytes]]:
    """
    Executes shell command with possible pipe and redirect symbols "|><".
    Returns tuple: (exit_code, is_timeout, output)
    """
    log.trace("input command: '%s' with extra_env %s", cmd, extra_env)

    extra_env = extra_env or {}
    hang_timeout_seconds = float(timeout_sec)
    kill_after = max(int(hang_timeout_seconds * 0.2), 2)
    allow_to_run_seconds = int(hang_timeout_seconds)
    timeout_total = kill_after + allow_to_run_seconds + 3.0
    argv = [
        "timeout",
        "--kill-after",
        "%ds" % kill_after,
        "-s",
        "SIGTERM",
        "%ds" % allow_to_run_seconds,
        "sh",
        "-c",
        cmd,
    ]
    exit_code = None
    output = None

    env = os.environ.copy()
    env.update(extra_env)

    log.trace("starting command '%s' with env %s", " ".join(argv), env)

    try:
        inst = Popen(
            argv,
            env=env,
            shell=False,
            stdout=PIPE,
            stderr=STDOUT,
        )
        exit_code, output = _get_exitcode_and_output(inst, timeout_total)

    except TimeoutExpired:
        inst.kill()
        inst.wait(3.0)

        try:
            exit_code, output = _get_exitcode_and_output(inst, timeout_total)
        except TimeoutExpired:
            inst.kill()
            inst.wait(3.0)

    except SubprocessError:
        log.error("Wasn't able to start process with command '%s'", cmd)
        return (None, False, None)

    if exit_code in (124, 137):  # timeout utility return codes
        log.verbose3("timeout utility returned exit code %d", exit_code)
        return (None, True, None)

    return (exit_code, exit_code is None, output)


def run_interactive_shell_cmd(
    cmd: str, extra_env: Optional[Dict[str, str]] = None
) -> Tuple[Optional[int], bytes]:
    """
    Executes shell command with possible pipe and redirect symbols "|><".
    User has to ensure command exits (e.g. with timeout tool).
    Returns tuple: (exit_code | None, output)
    """
    log.trace("input command: '%s' with extra_env %s", cmd, extra_env)

    extra_env = extra_env or {}
    argv = [
        "sh",
        "-c",
        cmd,
    ]
    exit_code = None
    output = b""
    env = os.environ.copy()
    env.update(extra_env)
    log.trace("starting command '%s' with env %s", " ".join(argv), env)

    try:
        inst = Popen(
            argv,
            env=env,
            shell=False,
            stdout=PIPE,
            stderr=STDOUT,
            # bufsize=1,
        )
        for line in inst.stdout:
            output += line

        if inst.poll() is not None:
            inst.terminate()
            if inst.poll() is not None:
                inst.kill()
        exit_code = inst.wait()
    except SubprocessError:
        log.error("Wasn't able to start process with command '%s'", cmd)

    return (exit_code, output.rstrip(b"\n"))


def _get_exitcode_and_output(inst: Popen, timeout_sec: float):
    output, _ = inst.communicate(timeout=timeout_sec)
    exit_code = inst.returncode
    return (exit_code, output)


def make_env_shell_str(env: Dict[str, str]) -> Optional[str]:
    """
    Transforms env dict to string suitable for use in shell
    Returns None for empty dict
    """
    env = env or {}

    if not env:
        return None

    result: List[str] = []
    for k, v in env.items():
        value = v
        if "$" in v or " " in v:
            q = '"'
            if q in v:
                q = "'"
            value = f"{q}{v}{q}"

        result.append(f"{k}={value}")

    return " ".join(result)


def remove_prefix_env(cmdline: str) -> str:
    """
    Return `cmdline` without preceeding env variables.
    Original `cmdline` is returned if it doesn't start with "env ".
    """

    if not cmdline.startswith("env "):
        return cmdline

    cmd = cmdline.strip()
    cmd = shlex.split(cmd)[1:]

    for i, arg in enumerate(cmd):
        if "=" not in arg:
            return " ".join(cmd[i:])

    return " ".join(cmd)


def prepare_run_args_for_shell(run_args: List[str], sample_path: str) -> str:
    """
    Generate shell-compatible run arguments (binary name not included).
    If @@ is found in run_args, return run_args with quoted sample path instead of @@.
    If @@ is not found in run_args, return run_args with input redirected from quoted sample path.
    """
    str_args = " ".join(run_args)

    if "@@" in str_args:
        return str_args.replace("@@", f'"{sample_path}"')
    return str_args + f' < "{sample_path}"'


def get_process_children(pid: int, recursive: bool = False) -> List[psutil.Process]:
    """
    Return list of children `psutil.Process`es for given `pid`.
    In case of errors raises ProcessException.
    """
    try:
        p = psutil.Process(pid=pid)
    except psutil.Error as e:
        raise ProcessException(f"wasn't able to get children pids for pid {pid}") from e

    return p.children(recursive=recursive)
