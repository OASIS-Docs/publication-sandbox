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

"""Markdown-to-HTML conversion stage.

:class:`HtmlConverter` runs pandoc, then applies the OASIS post-processing
chain documented in ``TRANSFORMS.md``. The chain is not a monolithic method:
each fix-up is an :class:`~pipeline.html_transforms.HtmlTransform` subclass,
and the contractual order is the :attr:`HtmlConverter.TRANSFORMS` tuple — one
declared place to read it, test it, or extend it (a consumer with an extra
fix-up subclasses the converter and overrides the tuple; nobody edits a
90-line method).
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from typing import ClassVar, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import PipelineStep
from .html_transforms import (
    DropLogoFigures,
    DropNavBlocks,
    EnforceSingleLogo,
    FixTopBanner,
    HtmlTransform,
    InjectMetaDescription,
    LinkifyPlainUrls,
    LocalizeCss,
    LocalizeImages,
    NormalizeSameDocAnchors,
    RelativizeSameScopeLinks,
    RemoveBaseHref,
    RemoveDuplicateHeadingAnchors,
    StripPandocHeader,
)
from .markdown_formatter import MarkdownFormatter

logger = logging.getLogger(__name__)


class HtmlConverter(PipelineStep):
    """Convert a Markdown file to OASIS-styled HTML with post-processing.

    This is the ``--md-to-html`` half of step 1. Construction extracts the
    document's meta description and title from the *current* Markdown source and
    resolves the canonical published URL, so the caller must construct the
    converter before any in-place Markdown formatting if it wants those values
    taken from the pre-formatted source (matching historical behavior).
    """

    #: The OASIS post-processing chain, in contractual order (TRANSFORMS.md).
    #: This tuple IS the contract: reorder or extend it here, nowhere else.
    TRANSFORMS: ClassVar[tuple[type[HtmlTransform], ...]] = (
        StripPandocHeader,
        InjectMetaDescription,
        RemoveBaseHref,
        DropLogoFigures,
        DropNavBlocks,
        EnforceSingleLogo,
        FixTopBanner,
        RemoveDuplicateHeadingAnchors,
        NormalizeSameDocAnchors,
        LinkifyPlainUrls,
        LocalizeCss,
        LocalizeImages,
        RelativizeSameScopeLinks,
    )

    def __init__(
        self,
        md_file: str,
        output_file: str,
        git_repo_basedir: Optional[str] = None,
        md_dir: Optional[str] = None,
    ) -> None:
        """Resolve paths, extract title/description, and prepare output dirs."""
        self.md_file = self.sanitize_file_path(md_file)
        self.output_file = self.sanitize_file_path(output_file)
        self.git_repo_basedir = (
            self.sanitize_file_path(git_repo_basedir) if git_repo_basedir else None
        )
        self.md_dir = self.sanitize_file_path(md_dir) if md_dir else None

        logger.info("Initialized MarkdownToHtmlConverter with:")
        logger.info("  Markdown File: %s", self.md_file)
        logger.info("  Output File: %s", self.output_file)
        logger.info("  Git Repo Base Dir: %s", self.git_repo_basedir)
        logger.info("  Markdown Directory: %s", self.md_dir)

        self.meta_description = self._extract_meta_description(step=1)
        self.html_title = self._extract_html_title(step=2)

        out_dir = os.path.dirname(self.output_file)
        self.styles_dir = os.path.join(out_dir, self.styles_subdir)
        self.images_dir = os.path.join(out_dir, self.images_subdir)
        self.mkdirp(self.images_dir)

        # Parallel-safe pandoc scratch file, colocated with the output (the
        # old CWD-relative 'temp_output.html' made two concurrent conversions
        # clobber each other).
        self._temp_output = os.path.join(
            out_dir or ".", f".pandoc-tmp-{os.getpid()}.html"
        )

        local_styles_css = os.path.join(self.styles_dir, "styles.css")
        if os.path.exists(local_styles_css):
            self.css_ref_for_pandoc = os.path.join(self.styles_subdir, "styles.css")
        else:
            self.css_ref_for_pandoc = os.path.join(self.base_url, self.css_file_name)

        self.base_href_remote = self._construct_abs_doc_url(
            self.git_repo_basedir, self.md_dir
        )
        self._abs_doc_parsed = urlparse(self.base_href_remote)
        self._abs_doc_dir = (
            (self._abs_doc_parsed.path.rsplit("/", 1)[0] + "/")
            if self._abs_doc_parsed.path
            else "/"
        )

    # --------------------- document-context helpers ---------------------

    def path_tail_if_same_scope(self, url: str) -> Optional[str]:
        """Return the path tail if ``url`` lives under the published doc dir.

        The document context the transforms consult when deciding whether an
        absolute URL can be rewritten to a document-relative one.
        """
        try:
            p = urlparse(url)
        except Exception:
            return None
        if not p.scheme or not p.netloc:
            return None
        if (p.scheme, p.netloc) != (
            self._abs_doc_parsed.scheme,
            self._abs_doc_parsed.netloc,
        ):
            return None
        if not p.path.startswith(self._abs_doc_dir):
            return None
        return p.path[len(self._abs_doc_dir):]

    def _extract_meta_description(self, step: int) -> str:
        """Return the doc's meta description from an HTML comment or front matter."""
        logger.info("Step %s: Extracting meta description from: %s", step, self.md_file)
        try:
            with open(self.md_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("<!--") and "description:" in line.lower():
                        desc_start = line.lower().find("description:") + len("description:")
                        desc_end = line.find("-->")
                        if desc_end > desc_start:
                            return line[desc_start:desc_end].strip()
                    elif line.strip().startswith("description:"):
                        return line.split(":", 1)[1].strip().strip("\"'")
            logger.warning("Step %s: No meta description found.", step)
            return "-"
        except Exception:
            logger.error("Step %s: Error extracting meta description", step, exc_info=True)
            return "-"

    def _extract_html_title(self, step: int) -> str:
        """Return the document title from the first Markdown H1 (``# ``)."""
        logger.info("Step %s: Extracting HTML title from: %s", step, self.md_file)
        try:
            with open(self.md_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# "):  # first H1
                        return line.strip("# ").strip()
            logger.warning("Step %s: No HTML title found.", step)
            return "-"
        except Exception:
            logger.error("Step %s: Error extracting HTML title", step, exc_info=True)
            return "-"

    def _construct_abs_doc_url(
        self, git_repo_basedir: Optional[str], md_dir: Optional[str]
    ) -> str:
        """Resolve the canonical published URL for the output document."""
        if not git_repo_basedir or not md_dir:
            logger.warning("Git base or md_dir not provided; falling back to %s", self.base_url)
            return self.base_url
        relative_md_dir = os.path.relpath(md_dir, git_repo_basedir)
        if relative_md_dir == ".":
            relative_md_dir = ""
        if relative_md_dir:
            return f"{self.base_url}/{relative_md_dir}/{os.path.basename(self.output_file)}"
        return f"{self.base_url}/{os.path.basename(self.output_file)}"

    # ------------------------------ stages ------------------------------

    def _run_pandoc(self, step: int) -> None:
        """Run pandoc to produce the scratch HTML (standalone, with TOC)."""
        logger.info("Step %s: Running pandoc.", step)
        cmd = [
            "pandoc",
            self.md_file,
            "-f", "markdown+autolink_bare_uris+hard_line_breaks",
            "-c", self.css_ref_for_pandoc,
            "-s",
            "-o", self._temp_output,
            "--metadata", f"title={self.html_title}",
            "--toc",
        ]
        logger.debug("Pandoc command: %s", " ".join(cmd))
        self._run_subprocess(cmd)
        logger.info("Step %s: pandoc OK.", step)

    def _post_process_html(self, html: str, step: int) -> str:
        """Run the :attr:`TRANSFORMS` chain over the pandoc output."""
        logger.info("Step %s: Post-processing HTML.", step)
        soup = BeautifulSoup(html, "html.parser")
        for transform_cls in self.TRANSFORMS:
            transform = transform_cls()
            logger.debug("Applying transform: %s", transform.name)
            soup = transform.apply(soup, self)
        final = str(soup)
        logger.info("Step %s: Post-processing complete.", step)
        return final

    def ensure_toc_title(self) -> None:
        """Insert a ``# Table of Contents`` heading before an untitled TOC list."""
        logger.info("Ensuring TOC title exists.")
        try:
            with open(self.md_file, "r", encoding="utf-8") as f:
                content = f.read()
            toc_found = re.search(r"(- \[.*\]\(.*\))", content)
            toc_title_present = re.search(
                r"^\s*#+\s*Table of Contents\s*$", content, re.IGNORECASE | re.MULTILINE
            )
            if toc_found and not toc_title_present:
                lines = content.split("\n")
                toc_indices = [
                    i for i, line in enumerate(lines) if re.match(r"- \[.*\]\(.*\)", line)
                ]
                if toc_indices:
                    lines.insert(toc_indices[0], "\n# Table of Contents")
                    with open(self.md_file, "w", encoding="utf-8") as f2:
                        f2.write("\n".join(lines))
                    logger.info("Inserted TOC title.")
        except Exception:
            logger.error("Error ensuring TOC title", exc_info=True)

    def convert(self) -> None:
        """Run the full Markdown-to-HTML conversion, writing ``output_file``.

        Ensures a TOC title, runs pandoc into the scratch file, post-processes
        through the transform chain, writes the result, and always removes the
        scratch file.
        """
        try:
            step = 3
            logger.info("Step %s: Begin conversion.", step)
            self.ensure_toc_title(); step += 1
            self._run_pandoc(step=step); step += 1
            html_content = self._read_file(self._temp_output)
            final_html = self._post_process_html(html_content, step=step); step += 1
            self._write_file(self.output_file, final_html)
            logger.info("Step %s: Conversion done.", step)
        except Exception:
            logger.error("Conversion error", exc_info=True)
            raise
        finally:
            if os.path.exists(self._temp_output):
                os.remove(self._temp_output)
                logger.debug("Removed %s", self._temp_output)

    def run(self) -> None:
        """Execute the conversion stage (alias for :meth:`convert`)."""
        self.convert()


def main() -> None:
    """CLI entry point for step 1: Markdown formatting and/or HTML conversion.

    Preserves the historical contract:
    ``<md_file> <git_repo_basedir> <md_dir> [--test] [--md-format] [--md-to-html]``.
    The converter is constructed before Prettier runs so the title and meta
    description are read from the pre-formatted Markdown, matching prior behavior.
    """
    parser = argparse.ArgumentParser(description="Markdown to HTML Converter")
    parser.add_argument("md_file", type=str, help="Path to the markdown file")
    parser.add_argument("git_repo_basedir", type=str, help="Base directory of git repository")
    parser.add_argument("md_dir", type=str, help="Directory containing markdown file")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--md-format", action="store_true", help="Run Prettier to format the markdown file")
    parser.add_argument("--md-to-html", action="store_true", help="Convert markdown file to HTML")
    args = parser.parse_args()

    if args.test:
        git_repo_basedir = "/github/workspace"
        md_dir = git_repo_basedir
        md_file = os.path.join(md_dir, "example.md")
        output_file = os.path.join(md_dir, "example.html")
    else:
        git_repo_basedir = PipelineStep.sanitize_file_path(args.git_repo_basedir)
        md_dir = PipelineStep.sanitize_file_path(args.md_dir)
        md_file = PipelineStep.sanitize_file_path(args.md_file)
        output_file = os.path.join(md_dir, os.path.basename(md_file).replace(".md", ".html"))

    converter = HtmlConverter(md_file, output_file, git_repo_basedir, md_dir)

    if args.md_format:
        MarkdownFormatter(md_file).run_prettier()
        logger.info("Markdown formatting completed.")

    if args.md_to_html:
        converter.convert()
        logger.info("Markdown to HTML conversion completed.")
