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

from typing import List, Dict, Optional

import os
import shutil
from bugbane.modules.log import getLogger

log = getLogger(__name__)

from .minimizers.minimizer import (
    MinimizerUsingProgram,
    MinimizerError,
    MinimizerFileAction,
)
from .minimizers.factory import MinimizerFactory
from .minimizers.hashsum_minimizer import HashSumMinimizer


def deduplicate_by_hashes(
    masks: List[str], dest: str, file_action: MinimizerFileAction
) -> Optional[int]:
    """
    Basic deduplication mechanism based on file hashes.
    Function returns number of resulting files
    """

    minimizer = HashSumMinimizer()
    count = minimizer.run(masks, dest, file_action)
    return count


def deduplicate_by_tool(
    masks: List[str],
    dest: str,
    tool_name: str,
    program: str,
    run_args: Optional[List[str]],
    run_env: Optional[Dict[str, str]],
    prog_timeout_ms: Optional[int],
    tool_timeout_sec: int,
) -> Optional[int]:
    try:
        minimizer: MinimizerUsingProgram = MinimizerFactory.create(tool_name)
    except TypeError as e:
        raise MinimizerError(f"wasn't able to create minimizer: {e}") from e

    minimizer.configure(
        program=program,
        run_args=run_args,
        run_env=run_env,
        prog_timeout_ms=prog_timeout_ms,
        tool_timeout_sec=tool_timeout_sec,
    )
    log.verbose1("Using tool minimizer %s", minimizer.__class__.__name__)

    count = minimizer.run(masks, dest)
    return count


def sync_files_by_names(src_dir: str, dst_dir: str, max_sample_size: int) -> int:
    """
    Copies files from source to destination if destination doesn't already
    contain same file names.
    Skips files bigger than `max_sample_size` (specified in bytes).
    Returns number of newly copied files.
    NOTE: Destination directory must exist.
    NOTE: This method is not recursive.
    """

    if not src_dir or not os.path.exists(src_dir) or os.path.isfile(src_dir):
        log.debug("Bad source directory %s", src_dir)
        return 0

    src_files = os.listdir(src_dir)

    log.verbose2(
        "Have %d entries to synchronize from %s to %s", len(src_files), src_dir, dst_dir
    )

    if max_sample_size > 0:
        bail_on_bad_size = lambda p: os.stat(p).st_size > max_sample_size
    else:
        bail_on_bad_size = lambda _: False

    count = 0
    for src_name in src_files:
        src_file = os.path.join(src_dir, src_name)
        if not os.path.isfile(src_file):
            continue

        dst_file = os.path.join(dst_dir, src_name)
        if os.path.exists(dst_file):
            continue

        if bail_on_bad_size(src_file):
            continue

        shutil.copyfile(src_file, dst_file, follow_symlinks=True)
        count += 1
    return count
