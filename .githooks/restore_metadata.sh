#!/usr/bin/env bash
# Copyright 2025-2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
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
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
set -Eeuo pipefail
IFS=$'\n\t'
# shellcheck disable=SC2154
trap 'rc=$?; echo "ERROR: ${BASH_SOURCE[0]}:${LINENO} exited with $rc" >&2' ERR
repo_root="$(git rev-parse --show-toplevel)"
metadata_file="${repo_root}/.file-metadata"
temp_metadata_file="${repo_root}/.file-metadata.tmp"

date_touch() {
  if date -r 0 +%s >/dev/null 2>&1; then
    # BSD/macOS
    date -r "$1" +%Y%m%d%H%M.%S
  else
    # GNU
    date -d "@$1" +%Y%m%d%H%M.%S
  fi
}

[[ -f "${metadata_file}" ]] || exit 0
trap 'rm -f "${temp_metadata_file}"' EXIT

while IFS=' ' read -r epoch rest; do
  file="${rest}"
  # skip untracked or ignored
  if ! git ls-files --error-unmatch -- "$file" >/dev/null 2>&1 || git check-ignore -q -- "$file"; then
    continue
  fi
  if [[ -f "$file" ]]; then
    ts="$(date_touch "$epoch")"
    touch -t "$ts" -- "$file" 2>/dev/null || touch -t "$ts" "$file"
    echo "$epoch $file" >> "${temp_metadata_file}"
  fi
done < "${metadata_file}"

if [[ -f "${temp_metadata_file}" ]]; then
  mv -f -- "${temp_metadata_file}" "${metadata_file}"
else
  rm -f -- "${metadata_file}"
fi
