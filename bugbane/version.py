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

"""Module describing BugBane version and helper utils."""

__version__ = "0.6.0.dev"
"""BugBane version"""


def name_version_description(prog_name: str, description: str) -> str:
    """
    Return provided program name `prog_name` with the current project version
    and `description` provided.
    For use with argparse.ArgumentParser.
    """
    return f"{name_version(prog_name)} - {description}"


def name_version(prog_name: str) -> str:
    """
    Return provided program name `prog_name` with the current project version.
    For use in things like argument parsing and help messages.
    """
    return f"{prog_name} v{__version__}"
