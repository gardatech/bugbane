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

from typing import Optional
from abc import ABC, abstractmethod


class FuzzerInfo(ABC):
    """Class representing various information about fuzzer"""

    REPRODUCE_REQUIRED = True
    """
    True if crashes & hangs need to be reproduced after fuzzing.
    False if fuzzer does this job
    """

    COVERAGE_REQUIRED = True
    """
    True if coverage need to be collected after fuzzing.
    False if fuzzer does this job
    """

    @abstractmethod
    def initial_samples_required(self) -> bool:
        """
        Return True if fuzzer can't work without initial corpus.
        Return False if fuzzer can start from scratch
        """

    @abstractmethod
    def input_dir(self, sync_dir: str) -> str:
        """
        Return path to directory that should contain input samples for fuzzer.
        Examples: "sync_dir/../in", "sync_dir/corpus"
        """

    @abstractmethod
    def sample_mask(self, sync_dir: str, instance_name: str) -> str:
        """
        Return mask for samples in corpus for fuzzer instance named `instance_name`
        (e.g. "out/myfuzzer/queue/id*").
        `instance_name` may be "*" to match all instances
        """

    @abstractmethod
    def crash_mask(self, sync_dir: str, instance_name: str) -> str:
        """
        Return mask for crashes for fuzzer instance named `instance_name`
        (e.g. "out/myfuzzer/crashes/id*").
        `instance_name` may be "*" to match all instances
        """

    @abstractmethod
    def hang_mask(self, sync_dir: str, instance_name: str) -> str:
        """
        Return mask for hangs in corpus for fuzzer instance named `instance_name`
        (e.g. "out/myfuzzer/hangs/id*").
        `instance_name` may be "*" to match all instances
        """

    @abstractmethod
    def stats_dir(self, sync_dir: str) -> str:
        """
        Return directory from which to read fuzzer statistics, e.g. ./out or ./
        """

    @abstractmethod
    def coverage_dir(self, sync_dir: str) -> Optional[str]:
        """
        Return directory with coverage files or None if fuzzer doesn't collect coverage
        """
