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

from typing import List, Optional, Callable
from abc import ABC, abstractmethod

import os
import shutil
from enum import Enum, auto

import logging

log = logging.getLogger(__name__)


class MinimizerError(Exception):
    """Exception class for errors that occur in Minimizer class"""


class MinimizerFileAction(Enum):
    COPY = auto()
    MOVE = auto()


def copy_file_action(src: str, dst: str):
    try:
        shutil.copyfile(src, dst)
    except OSError as e:
        raise MinimizerError(f"while copying {src} to {dst}: {e}") from e


def move_file_action(src: str, dst: str):
    try:
        shutil.move(src, dst, copy_function=shutil.copyfile)
    except OSError as e:
        raise MinimizerError(f"while copying {src} to {dst}: {e}") from e


class Minimizer(ABC):
    """
    ABC for Minimizer classes
    """

    def run(
        self,
        src_masks: List[str],
        dest: str,
        file_action: MinimizerFileAction = MinimizerFileAction.COPY,
    ) -> Optional[int]:
        """
        Run minimizing tool on each of src_masks.
        NOTE: directory `dest` will be removed if already exists.
        """

        if file_action == MinimizerFileAction.COPY:
            action_func = copy_file_action
        else:
            action_func = move_file_action

        self._cleanup_dest_dir(dest)

        result = 0

        for mask in src_masks:
            log.verbose1("Minimizing %s...", mask)
            count = self.run_one(mask, dest, action_func)
            result += count or 0

        return result or None

    def _cleanup_dest_dir(self, dest):
        if not os.path.exists(dest):
            return
        if not os.listdir(dest):
            return

        log.info("NOTE: removing existing destination directory %s", dest)
        try:
            shutil.rmtree(dest)
            os.makedirs(dest)
        except OSError as e:
            raise MinimizerError(
                f"wasn't able to recreate destination directory {dest}. Message: {e}",
            ) from e

    @abstractmethod
    def run_one(
        self,
        mask: str,
        dest: str,
        file_action_func: Callable[[str, str], None],
    ) -> Optional[int]:
        """
        Run minimizing tool on one sample mask, appending results to dest.
        Return resulting number of files
        """


class MinimizerUsingProgram(Minimizer):
    """Base class for afl-cmin and other tools that require running program with arguments"""

    def __init__(self):
        super().__init__()

        self.program: Optional[str] = None
        self.run_args: Optional[List[str]] = None
        self.timeout_sec = 60 * 60

    def configure(
        self,
        program: str,
        run_args: Optional[List[str]] = None,
        timeout_sec: int = 60 * 60,
    ):
        self.program = program
        self.run_args = run_args
        self.timeout_sec = timeout_sec
