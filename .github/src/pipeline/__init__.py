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

"""OASIS document-publication pipeline package.

Shared infrastructure lives in :class:`~pipeline.base.PipelineStep`; each
concrete stage is a subclass:

* :class:`~pipeline.markdown_formatter.MarkdownFormatter` — Prettier formatting.
* :class:`~pipeline.html_converter.HtmlConverter` — pandoc + OASIS HTML fix-ups.
* :class:`~pipeline.pdf_preprocessor.PdfPreprocessor` — code-block CSS injection.
* :class:`~pipeline.pdf_renderer.PdfRenderer` — wkhtmltopdf rendering.
"""

from __future__ import annotations

from .base import PipelineStep
from .html_converter import HtmlConverter
from .markdown_formatter import MarkdownFormatter
from .pdf_preprocessor import PdfPreprocessor
from .pdf_renderer import PdfRenderer

__all__ = [
    "PipelineStep",
    "MarkdownFormatter",
    "HtmlConverter",
    "PdfPreprocessor",
    "PdfRenderer",
]
