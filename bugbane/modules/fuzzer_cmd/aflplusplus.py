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

from typing import Optional, List, Dict

import os
from copy import copy
from math import ceil

from bugbane.modules.log import getLogger

log = getLogger(__name__)

from bugbane.modules.build_type import BuildType
from bugbane.modules.string_utils import replace_part_in_str_list
from bugbane.modules.process import make_env_shell_str

from .fuzzer_cmd import FuzzerCmd, FuzzerCmdError
from .factory import FuzzerCmdFactory


@FuzzerCmdFactory.register("AFL++")
class AFLplusplusCmd(FuzzerCmd):
    """AFL++ commands generator"""

    def generate_one(
        self, input_corpus: str, output_corpus: str, run_env: Dict[str, str]
    ) -> str:
        env_copy = self._replace_ld_preload(run_env)
        env_str = make_env_shell_str(env_copy)
        cmd = f"afl-fuzz -i {input_corpus} -o {output_corpus} -m none -S $name -- $appname $run_args"

        if env_str:
            return f"env {env_str} {cmd}"

        return cmd

    def _replace_ld_preload(self, run_env: Dict[str, str]) -> Dict[str, str]:
        """
        Replace LD_PRELOAD with AFL_PRELOAD in input `run_env` dictionary.
        Return new run_env dictionary.
        """
        env_copy = dict(run_env)

        if env_copy and "LD_PRELOAD" in env_copy:
            env_copy["AFL_PRELOAD"] = env_copy.pop("LD_PRELOAD")

        return env_copy

    def stats_cmd(self, sync_dir: str) -> Optional[str]:
        return f"watch -t -n 5 afl-whatsup -s {sync_dir}"

    def make_replacements(
        self,
        cmds: List[str],
        builds: Dict[BuildType, str],
        dict_path: Optional[str] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Try to copy recommended AFL++ CI Fuzzing setup:
        https://github.com/AFLplusplus/AFLplusplus#ci-fuzzing

        Return reproduce spec: {"AFL++": {"binary_path": ["samples_root_dir", ...] ...}}
        """

        count = len(cmds)

        with_timeout = self.add_timeout_to_cmd(cmds[0], timeout_ms)
        for i in range(count):
            cmds[i] = copy(with_timeout)

        first = 0
        if count == 1:
            main_offset = 0
        else:
            main_offset = 1

        last = count - 1
        sanitizer_builds = [
            path for bt, path in builds.items() if bt.is_static_sanitizer()
        ]
        sanitizer_count = len(sanitizer_builds)

        default_bt = self._select_default_build_type(list(builds))
        log.verbose3("Using build type %s as default", default_bt.name.upper())

        specs = [builds[default_bt]] * count

        # 1 deterministic main with dictionary
        new_part = " -D -M $name "
        if dict_path:
            new_part += f"-x {dict_path} "
        replace_part_in_str_list(cmds, " -S $name ", new_part, 1, first)

        num_basic_builds = count - sanitizer_count
        if num_basic_builds < 0:
            raise FuzzerCmdError("not enough cores for all sanitizer builds")

        # last cores are used for fuzzing sanitizer builds
        for i, san_build in enumerate(sanitizer_builds, start=1):
            num, start = (1, last - sanitizer_count + i)
            replace_part_in_str_list(cmds, "$appname", san_build, num, start)
            replace_part_in_str_list(specs, builds[default_bt], san_build, num, start)

        self._add_laf_build(builds, cmds, specs, default_bt)
        self._add_cmplog_build(builds, cmds, main_offset)

        # replace builds in all the remaining commands to basic build:
        replace_part_in_str_list(cmds, "$appname", builds[default_bt], 1, first, last)

        if count > 1:
            self._add_mmopt_args(cmds, main_offset)
            self._add_old_queue_processing_args(cmds, main_offset)

        spec_separator = ";"
        specs = ["$name" + spec_separator + spec for spec in specs]

        # this should be final step when editing cmds:
        base_inst_name = os.path.basename(builds[default_bt])
        self._add_fuzzer_instance_names(cmds, specs, base_inst_name)

        return {"AFL++": self._specs_to_dict(specs, spec_separator)}

    def _select_default_build_type(self, builds: List[BuildType]) -> BuildType:
        """Select build type to be used in commands by default."""

        build_type_priority = [
            BuildType.BASIC,
            BuildType.ASAN,
            BuildType.UBSAN,
            BuildType.CFISAN,
            BuildType.LAF,
            BuildType.LSAN,
            BuildType.MSAN,
            BuildType.TSAN,
            BuildType.COVERAGE,
        ]

        default_bt = builds[0]
        for bt in build_type_priority:
            if bt in builds:
                return bt

        return default_bt

    def _add_laf_build(
        self,
        builds: Dict[BuildType, str],
        cmds: List[str],
        specs: List[str],
        default_bt: BuildType,
    ) -> None:
        """Make 10% of cmds use LAF build, skipping first 40% of cmds."""

        if BuildType.LAF not in builds:
            return

        count = len(cmds)
        first = 0
        p10 = ceil(count * 0.1)
        p40 = ceil(count * 0.4)

        num, start, end = (1, first + p40, first + p40 + p10)
        replace_part_in_str_list(
            cmds, "$appname", builds[BuildType.LAF], num, start, end
        )
        replace_part_in_str_list(
            specs, builds[default_bt], builds[BuildType.LAF], num, start, end
        )

    def _add_cmplog_build(
        self,
        builds: Dict[BuildType, str],
        cmds: List[str],
        main_offset: int,
    ) -> None:
        """If cmplog present in builds, add it to 40% of cmds."""

        if BuildType.CMPLOG not in builds:
            return

        count = len(cmds)
        first = 0
        last = count - 1
        p40 = ceil(count * 0.4)
        p40_60 = ceil(p40 * 0.6)  # out of 40%: 60% -l2, 40% -l3

        # first 40% of cores use cmplog build
        replace_part_in_str_list(
            cmds,
            " -- ",
            f" -c {builds[BuildType.CMPLOG]} -- ",
            1,
            first + main_offset,
            first + p40,
        )
        # 60% of cmplog use -l 2
        replace_part_in_str_list(
            cmds, " -- ", " -l 2 -- ", 1, first + main_offset, first + p40_60
        )

        if count < 2:
            return

        # rest of cmplog use -l 3
        replace_part_in_str_list(
            cmds, " -- ", " -l 3 -- ", 1, first + p40_60 + 1, first + p40
        )

        # TODO: remove useless -l when no -c was passed
        # solve overlap in favor of -l 2
        replace_part_in_str_list(cmds, " -l 2 -l 3 -- ", " -l 2 -- ", 1, first, last)

    def _add_mmopt_args(self, cmds: List[str], main_offset: int) -> None:
        """Add mmopt -L 0 to 40% of cmds, skipping first 20% of cmds."""

        first = 0
        count = len(cmds)
        p20 = ceil(count * 0.2)
        p40 = ceil(count * 0.4)

        replace_part_in_str_list(
            cmds,
            " -- ",
            " -L 0 -- ",
            1,
            first + main_offset + p20,
            first + main_offset + p20 + p40,
        )

    def _add_old_queue_processing_args(self, cmds: List[str], main_offset: int) -> None:
        """Make 20% of cmds use old queue processing -Z, skipping first 40% of cmds."""

        first = 0
        count = len(cmds)
        p20 = ceil(count * 0.2)
        p40 = ceil(count * 0.4)

        replace_part_in_str_list(
            cmds,
            " -- ",
            " -Z -- ",
            1,
            first + main_offset + p40,
            first + main_offset + p40 + p20,
        )

    def _add_fuzzer_instance_names(
        self, cmds: List[str], specs: List[str], base_inst_name: str
    ):
        """Replace $name in both cmds and specs with base_inst_name + index"""

        first = 0
        last = len(cmds) - 1

        for str_list in (cmds, specs):
            replace_part_in_str_list(
                str_list,
                "$name",
                base_inst_name + "$i",
                1,
                first,
                last,
            )

    def _specs_to_dict(
        self, specs: List[str], spec_separator: str
    ) -> Dict[str, List[str]]:
        """
        Convert list of strings like '/fuzz/basic/fuzzer;sync_dir' to
        dictionary, where '/fuzz/basic/fuzzer' becomes key and 'sync_dir' - value
        """
        result: Dict[str, List[str]] = {}
        for spec in specs:
            samples_subdir, app_path = spec.split(spec_separator, 1)
            if app_path in result:
                result[app_path].append(samples_subdir)
            else:
                result[app_path] = [samples_subdir]
        return result

    def add_timeout_to_cmd(self, cmd: str, timeout_ms: Optional[int]) -> str:
        if timeout_ms is None:
            return cmd

        timeout_ms = max(1, timeout_ms)
        return cmd.replace(" -- ", f" -t {timeout_ms} -- ")

    def make_one_tmux_capture_pane_cmd(
        self, tmux_session_name: str, window_index: int
    ) -> str:
        cmd = f"""tmux capture-pane -e -t {tmux_session_name}:{window_index} -S -5 -p \
                    | uniq \
                    | grep -e 'status check tool' -e 'american fuzzy lop' -A 35 \
                    | egrep -v '^tput: unknown terminfo' \
                    | cat -s \
                    | head -n -1"""
        return cmd
