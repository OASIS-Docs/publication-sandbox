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

"""Shared base class for the OASIS document-publication pipeline steps.

:class:`PipelineStep` owns every concern that the individual pipeline stages
would otherwise duplicate: the ``docs.oasis-open.org`` constants, file-path
sanitization, encoded file read/write, subprocess execution with error
reporting, and logging configuration. Concrete stages (Markdown formatting,
HTML conversion, PDF preprocessing, PDF rendering) subclass it and implement
:meth:`run`.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from abc import ABC, abstractmethod
from typing import Sequence

logger = logging.getLogger(__name__)


class PipelineStep(ABC):
    """Abstract base for a single stage of the publication pipeline.

    Subclasses implement :meth:`run` to perform their transform. All shared
    infrastructure — the canonical OASIS constants and the file/subprocess/
    logging helpers — lives here so it is defined exactly once.
    """

    # ---- Canonical docs.oasis-open.org constants (single source of truth) ----

    #: Canonical host for published OASIS artifacts.
    base_url: str = "https://docs.oasis-open.org"

    #: Remote stylesheet path (under :attr:`base_url`) used when no local CSS
    #: is present next to the generated HTML.
    css_file_name: str = "styles/markdown-styles-v1.7.3.css"

    #: Authoritative public URL for the OASIS logo image.
    logo_canonical_remote: str = "https://docs.oasis-open.org/templates/OASISLogo-v3.0.png"

    #: Matches any ``src`` that already points at the canonical logo filename.
    logo_ok_src_regex: re.Pattern[str] = re.compile(
        r".*/OASISLogo-v3\.0\.png$", re.IGNORECASE
    )

    #: Output subdirectory (relative to the HTML file) for localized images.
    images_subdir: str = "images"

    #: Output subdirectory (relative to the HTML file) for localized CSS.
    styles_subdir: str = "styles"

    # -------------------------- shared helpers --------------------------

    @staticmethod
    def sanitize_file_path(file_path: str) -> str:
        """Return a normalized, newline-free filesystem path.

        Strips surrounding whitespace, removes embedded newlines, and applies
        :func:`os.path.normpath`. The result is safe to hand to shell tools.
        """
        sanitized = os.path.normpath(file_path.strip().replace("\n", ""))
        logger.debug(
            "Sanitized file path: Original='%s' | Sanitized='%s'", file_path, sanitized
        )
        return sanitized

    @staticmethod
    def mkdirp(path: str) -> None:
        """Create ``path`` and any missing parents; no error if it exists."""
        os.makedirs(path, exist_ok=True)

    def _read_file(self, file_path: str) -> str:
        """Return the UTF-8 contents of ``file_path``; re-raise on OSError."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            logger.error("Failed to read %s", file_path, exc_info=True)
            raise

    def _write_file(self, file_path: str, content: str) -> None:
        """Write ``content`` to ``file_path`` as UTF-8; re-raise on OSError."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            logger.error("Failed to write %s", file_path, exc_info=True)
            raise

    def _run_subprocess(
        self, cmd: Sequence[str], *, capture: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Run ``cmd`` with ``check=True`` and report failures.

        With ``capture=False`` the child's stdout/stderr stream to the console
        (used for pandoc). With ``capture=True`` output is captured as text and
        returned on the completed process (used for wkhtmltopdf). A non-zero
        exit is logged and the :class:`subprocess.CalledProcessError` re-raised.
        """
        logger.debug("Running command: %s", " ".join(cmd))
        try:
            if capture:
                return subprocess.run(cmd, check=True, capture_output=True, text=True)
            return subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            logger.error(
                "Command failed with exit code %s: %s",
                exc.returncode,
                " ".join(cmd),
                exc_info=True,
            )
            raise

    @staticmethod
    def configure_logging(*, level: int = logging.INFO, log_file: str | None = None) -> None:
        """Configure root logging for an entry-point script.

        Always logs to the console; when ``log_file`` is given, also appends to
        that file. Uses the pipeline's standard ``asctime - levelname - message``
        format.
        """
        handlers: list[logging.Handler] = [logging.StreamHandler()]
        if log_file:
            handlers.append(logging.FileHandler(log_file))
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=handlers,
        )

    # ------------------------------ contract ------------------------------

    @abstractmethod
    def run(self) -> None:
        """Execute this pipeline stage. Implemented by each concrete subclass."""
        raise NotImplementedError
