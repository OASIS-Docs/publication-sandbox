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

"""Entry point for step 1: Markdown formatting and Markdown-to-HTML conversion.

Thin CLI shim over :mod:`pipeline.html_converter`. Preserves the historical
invocation contract exactly:

    step_1_markdown_to_html_converter_V3_0.py <md_file> <git_repo_basedir> \
        <md_dir> [--test] [--md-format] [--md-to-html]
"""

from __future__ import annotations

import logging
import os

from pipeline.html_converter import main

if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("markdown_conversion.log"), logging.StreamHandler()],
    )
    main()
