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

"""Markdown normalization stage: run Prettier over a Markdown source in place."""

from __future__ import annotations

import logging

from .base import PipelineStep

logger = logging.getLogger(__name__)


class MarkdownFormatter(PipelineStep):
    """Format a Markdown file in place with Prettier.

    This is the ``--md-format`` half of step 1. It rewrites ``md_file`` on disk
    using ``prettier --write`` and performs no other transformation.
    """

    def __init__(self, md_file: str) -> None:
        """Store the sanitized path to the Markdown file to be formatted."""
        self.md_file = self.sanitize_file_path(md_file)

    def run_prettier(self) -> None:
        """Format the Markdown file in place via ``prettier --write``.

        Re-raises :class:`subprocess.CalledProcessError` if Prettier fails.
        """
        logger.info("Running Prettier on Markdown.")
        self._run_subprocess(["prettier", "--write", self.md_file.strip()])

    def run(self) -> None:
        """Execute the formatting stage (alias for :meth:`run_prettier`)."""
        self.run_prettier()
