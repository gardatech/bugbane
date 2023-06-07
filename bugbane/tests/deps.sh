#!/bin/bash
# Tool to find uses of Python classes

# Copyright 2022-2023 Garda Technologies, LLC. All rights reserved.
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


declare -a paths
while [ $# -gt 0 ]; do
  case "$1" in
    --root=*)
      root_dir="${1#*=}"
      ;;
    *)
      [ ! -d "$1" ] && echo "Directory $1 doesn't exist!" && exit 1
      paths+=(`readlink -f "$1"`)
  esac
  shift
done

root_dir=${root_dir:-bugbane}
root_dir=`readlink -f $root_dir`
[ ! -d $root_dir ] && echo "Directory $root_dir doesn't exist!" && exit 1
[ ${#paths[@]} -lt 1 ] && echo "No paths specified" && exit 1

echo Checking $root_dir
echo "Paths to check: ${paths[@]}"

for path in "${paths[@]}"
do
  names=`grep -rPIho --include="*.py" '(?<=^class )\w+(?=\()' $path | sort | uniq`
  echo "$names" | while read -r name; do
    echo "Checking for '$name' from $path" >/dev/stderr
    grep -rwnI --include="*.py" --color=always $name $root_dir | grep -v -e "/tests/" # -e "$path"
  done
done

