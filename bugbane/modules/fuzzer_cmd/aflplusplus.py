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
from math import ceil

import logging

log = logging.getLogger(__name__)

from bugbane.modules.build_type import BuildType
from bugbane.modules.string_utils import replace_part_in_str_list

from .fuzzer_cmd import FuzzerCmd
from .factory import FuzzerCmdFactory


@FuzzerCmdFactory.register("AFL++")
class AFLplusplusCmd(FuzzerCmd):
    def generate_one(self, input_corpus: str, output_corpus: str) -> str:
        return f"afl-fuzz -i {input_corpus} -o {output_corpus} -m none -S $name -- $appname $run_args"

    def stats_cmd(self, sync_dir: str) -> Optional[str]:
        return f"watch -t -n 5 afl-whatsup -s {sync_dir}"

    def make_replacements(
        self, cmds: List[str], builds: Dict[BuildType, str]
    ) -> Dict[str, Dict[str, str]]:
        """
        Try to copy recommended AFL++ CI Fuzzing setup:
        https://github.com/AFLplusplus/AFLplusplus#ci-fuzzing

        Return reproduce spec: {"AFL++": {"binary_path": "samples_root_dir" ...}}
        """

        count = len(cmds)

        # calculate P% out of all cmds (cpu cores)
        p10 = ceil(count * 0.1)
        p20 = ceil(count * 0.2)
        p40 = ceil(count * 0.4)
        p40_60 = ceil(p40 * 0.6)  # for cmplog: 60% -l2, 40% -l3

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

        default_bt_priority = [
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

        default_bt = None
        for bt in default_bt_priority:
            if bt in builds:
                default_bt = bt
                break

        log.verbose3("Using build type %s as default", default_bt.name.upper())

        specs = [builds[default_bt]] * count

        # 1 deterministic main
        replace_part_in_str_list(cmds, " -S $name ", " -D -M $name ", 1, first)

        num_basic_builds = count - sanitizer_count
        if num_basic_builds < 0:
            raise ArithmeticError("not enough cores for all types of builds")

        # last cores are used for fuzzing sanitizer builds
        for i, san_build in enumerate(sanitizer_builds, start=1):
            num, start = (1, last - sanitizer_count + i)
            replace_part_in_str_list(cmds, "$appname", san_build, num, start)
            replace_part_in_str_list(specs, builds[default_bt], san_build, num, start)

        # 10% of cores use LAF build, skipping first 40% of cores
        if BuildType.LAF in builds:
            num, start, end = (1, first + p40, first + p40 + p10)
            replace_part_in_str_list(
                cmds, "$appname", builds[BuildType.LAF], num, start, end
            )
            replace_part_in_str_list(
                specs, builds[default_bt], builds[BuildType.LAF], num, start, end
            )

        # add cmplog to first 40% of cores:
        if BuildType.CMPLOG in builds:
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

            if count > 1:
                # rest (40%) of cmplog use -l 3
                replace_part_in_str_list(
                    cmds, " -- ", " -l 3 -- ", 1, first + p40_60 + 1, first + p40
                )
                # solve overlap in favor of -l 2
                replace_part_in_str_list(
                    cmds, " -l 2 -l 3 -- ", " -l 2 -- ", 1, first, last
                )
                # TODO: also remove useless -l when no -c were passed

        # replace builds in all the remaining commands to basic build:
        replace_part_in_str_list(cmds, "$appname", builds[default_bt], 1, first, last)

        if count > 1:
            # add mmopt -L 0 to 40% of all cores, skipping first 20% of cores:
            replace_part_in_str_list(
                cmds,
                " -- ",
                " -L 0 -- ",
                1,
                first + main_offset + p20,
                first + main_offset + p20 + p40,
            )

            # 20% of cores use old queue processing -Z, skipping first 40% of cores
            replace_part_in_str_list(
                cmds,
                " -- ",
                " -Z -- ",
                1,
                first + main_offset + p40,
                first + main_offset + p40 + p20,
            )

        specs = ["$name;" + spec for spec in specs]
        # replace fuzzer instance names (should be final step):
        replace_part_in_str_list(
            cmds,
            "$name",
            os.path.basename(builds[default_bt]) + "$i",
            1,
            first,
            last,
        )
        replace_part_in_str_list(
            specs,
            "$name",
            os.path.basename(builds[default_bt]) + "$i",
            1,
            first,
            last,
        )
        result = {}
        for spec in specs:
            samples_subdir, app_path = spec.split(";", 1)
            result[app_path] = samples_subdir

        return {"AFL++": result}

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
