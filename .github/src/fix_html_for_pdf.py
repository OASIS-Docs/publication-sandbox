#!/usr/bin/env python3
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

"""Entry point for the PDF HTML preprocessor.

Thin CLI shim over :mod:`pipeline.pdf_preprocessor`. Preserves the historical
invocation contract exactly:

    fix_html_for_pdf.py <html_file> [-o OUTPUT] [-v]
"""

from __future__ import annotations

from pipeline.pdf_preprocessor import main

if __name__ == "__main__":
    main()
