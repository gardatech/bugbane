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
import pprint

from .args import parse_args

from bugbane.modules.log import get_first_logger
from bugbane.modules.fuzz_data_suite import FuzzDataSuite, FuzzDataError

from .builders.factory import FuzzBuilderFactory
from .builders.base_builders import Builder, BuildError


def main(argv=None):
    """
    1. Load bugbane.json
    2. Run ./build.sh for each sanitizer and for coverage
    3. Collect build results from $BUILD_ROOT and save them to args.output
    """

    argv = argv or sys.argv[1:]
    args = parse_args(argv)
    log = get_first_logger(__name__, args.verbose)

    os.chdir(args.input)

    try:
        suite, bane_vars = FuzzDataSuite.unpack_from_fuzzing_suite_dir(args.input)
    except FuzzDataError as e:
        log.error("Wasn't able to load source fuzzing suite: %s", e)
        return 1
    log.verbose1("Loaded source fuzzing suite: %s", suite)
    log.verbose3("Loaded vars: %s", pprint.pformat(bane_vars, sort_dicts=False))

    builder_type = bane_vars.get("builder_type") or "AFL++LLVM"
    try:
        builder: Builder = FuzzBuilderFactory.create(builder_type)
    except TypeError as e:
        log.error("Wasn't able to create builder: %s", e)
        return 1
    bane_vars["builder_type"] = builder_type
    bane_vars["coverage_type"] = builder.get_coverage_type()

    builder.configure(
        build_cmd=bane_vars["build_cmd"],
        build_root=bane_vars["build_root"],
        build_store_dir=args.output,
        build_log_path=os.path.join(args.output, "build.log"),
    )
    log.trace(
        "builder.build_cmd=%s, builder.build_root=%s",
        builder.build_cmd,
        builder.build_root,
    )

    if "sanitizers" in bane_vars:
        builder.assign_build_types(bane_vars["sanitizers"])

    builder.ensure_required_build_types()
    log.trace("builder.build_types=%s", builder.build_types)

    try:
        builds_complete = builder.build_all()
    except BuildError as e:
        log.error("Build error: %s", e)
        return 1

    log.info("Build results: %s", args.output)
    log.info("[+] Build complete. Updating configuration file")

    tested_binary_path = bane_vars.get("tested_binary_path")
    tested_binary_name = os.path.basename(tested_binary_path)
    bane_vars["tested_binary_name"] = tested_binary_name

    bane_vars["sanitizers"] = [
        bt.name.upper() for bt in builds_complete if bt.is_static_sanitizer()
    ]

    bane_vars["src_root"] = os.path.normpath(args.input)

    suite.save_vars(bane_vars)

    return 0
