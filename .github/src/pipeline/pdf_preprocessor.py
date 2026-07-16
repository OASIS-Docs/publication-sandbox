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

"""HTML preprocessing stage for enhanced PDF code-block formatting.

:class:`PdfPreprocessor` embeds a targeted monospace/code-block stylesheet into
an HTML document without disturbing existing OASIS CSS, then tags ``<pre>`` and
inline ``<code>`` elements so wkhtmltopdf renders code cleanly. The injected CSS
is intentionally distinct from the renderer stage's CSS.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from bs4 import BeautifulSoup

from .base import PipelineStep

logger = logging.getLogger(__name__)


class PdfPreprocessor(PipelineStep):
    """Inject targeted code-block CSS into an HTML file for PDF rendering."""

    def __init__(self, html_file: Path, output_file: Path) -> None:
        """Store the input and output HTML paths for this preprocessing pass."""
        self.html_file = html_file
        self.output_file = output_file

    @staticmethod
    def get_perfect_code_css() -> str:
        """Return the targeted code-formatting CSS to embed in the document.

        These rules target only code elements and are marked ``!important`` so
        they win over inherited OASIS styles without replacing them. The block
        is preserved verbatim; wkhtmltopdf output depends on its exact content.
        """
        return """
    /* TARGETED MONOSPACE FIXES - PRESERVE ORIGINAL OASIS CSS */
    
    /* Code elements - monospace font only */
    code, pre, .sourceCode, .highlight, tt, kbd, samp {
        font-family: "Courier New", "Liberation Mono", "DejaVu Sans Mono", "Consolas", "Monaco", monospace !important;
        font-weight: normal !important;
        font-style: normal !important;
        letter-spacing: 0 !important;
        word-spacing: 0 !important;
        -webkit-font-feature-settings: normal !important;
        font-feature-settings: normal !important;
    }
    
    /* Inline code styling */
    code {
        font-size: 0.9em !important;
        background-color: #f5f5f5 !important;
        border: 1px solid #ddd !important;
        border-radius: 2px !important;
        padding: 1px 4px !important;
        white-space: nowrap !important;
    }
    
    /* Code blocks styling */
    pre {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 10px !important;
        margin: 10px 0 !important;
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        page-break-inside: auto !important;
    }
    
    pre code {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        white-space: pre-wrap !important;
        font-size: inherit !important;
    }
    
    /* Syntax highlighting blocks */
    .sourceCode, .highlight {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        border-radius: 4px !important;
        padding: 10px !important;
        margin: 10px 0 !important;
    }
    
    /* Language-specific code blocks */
    .json, .xml, .yaml, .bash, .shell, .python, .javascript, .http {
        font-size: 0.85em !important;
        line-height: 1.2 !important;
        background-color: #f8f8f8 !important;
        border: 1px solid #ccc !important;
        padding: 10px !important;
        white-space: pre-wrap !important;
    }
    
    /* Code in tables */
    table code, td code, th code {
        font-size: 0.8em !important;
        white-space: nowrap !important;
    }
    
    /* PDF-specific code formatting */
    @media print {
        code, pre, .sourceCode, .highlight {
            -webkit-print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
        
        pre {
            page-break-inside: auto !important;
            orphans: 2 !important;
            widows: 2 !important;
        }
    }
    
    /* Page setup - portrait with wider margins */
    @page {
        size: A4 portrait;
        margin: 2.5cm 2cm 2.5cm 2cm;
    }
    """

    def preprocess(self) -> None:
        """Read the input HTML, embed the code CSS, tag code elements, write out.

        Ensures a ``<head>`` exists, appends the code stylesheet (append, not
        prepend, so existing CSS keeps precedence), adds ``code-block`` /
        ``inline-code`` classes where missing, and writes the result to
        :attr:`output_file`.
        """
        logger.info(f"Preprocessing HTML: {self.html_file} -> {self.output_file}")

        # Read the HTML file
        with open(self.html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Parse HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Ensure document has a proper head section
        if not soup.head:
            head = soup.new_tag('head')
            if soup.html:
                soup.html.insert(0, head)
            else:
                soup.insert(0, head)

        # Add targeted CSS for code formatting
        # Note: Appending rather than prepending to preserve existing CSS precedence
        style_tag = soup.new_tag('style')
        style_tag.string = self.get_perfect_code_css()
        soup.head.append(style_tag)

        # Ensure proper CSS classes for code block elements
        for pre in soup.find_all('pre'):
            if not pre.get('class'):
                pre['class'] = ['code-block']

        # Add CSS classes to inline code elements
        for code in soup.find_all('code'):
            if code.parent and code.parent.name != 'pre':
                if not code.get('class'):
                    code['class'] = ['inline-code']

        # Write preprocessed HTML to output file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))

        logger.info(f"HTML preprocessing completed successfully: {self.output_file}")

    def run(self) -> None:
        """Execute the preprocessing stage (alias for :meth:`preprocess`)."""
        self.preprocess()


def main() -> None:
    """CLI entry point: ``fix_html_for_pdf.py <html_file> [-o OUT] [-v]``.

    Defaults the output to ``<stem>_fixed<suffix>`` beside the input, validates
    the input exists, and exits non-zero on failure — preserving the original
    contract exactly.
    """
    parser = argparse.ArgumentParser(
        description="Preprocess HTML for enhanced PDF code block formatting",
        epilog="This tool adds targeted monospace CSS while preserving existing styles and document structure."
    )

    parser.add_argument(
        "html_file",
        help="Input HTML file to preprocess"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output HTML file (default: same as input with _fixed suffix)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging based on verbosity level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    PipelineStep.configure_logging(level=log_level)

    # Determine output file path
    input_path = Path(args.html_file)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_stem(input_path.stem + "_fixed")

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    try:
        PdfPreprocessor(input_path, output_path).preprocess()
        print("HTML preprocessing completed successfully")
        print(f"Output: {output_path}")

    except Exception as e:
        logger.error(f"Preprocessing failed: {str(e)}")
        print(f"HTML preprocessing failed: {str(e)}")
        sys.exit(1)
