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

"""HTML-to-PDF rendering stage.

:class:`PdfRenderer` builds and executes the wkhtmltopdf command that turns a
preprocessed HTML file into the final PDF, with the pipeline's fixed page
geometry, running header, and footer. The command is constructed by
:meth:`build_command` so it can be asserted token-for-token in tests.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup

from .base import PipelineStep

logger = logging.getLogger(__name__)


class PdfRenderer(PipelineStep):
    """Render an HTML file to PDF with wkhtmltopdf, preserving OASIS styling.

    The renderer applies targeted improvements to code blocks while keeping the
    document's existing stylesheets, and produces a professional layout with a
    running header/footer and the pipeline's standard margins.
    """

    def __init__(self, html_file: str, output_pdf: str, base_dir: Optional[str] = None):
        """Resolve absolute paths and validate the input HTML exists."""
        self.html_file = Path(html_file).resolve()
        self.output_pdf = Path(output_pdf).resolve()
        self.base_dir = Path(base_dir).resolve() if base_dir else self.html_file.parent

        if not self.html_file.exists():
            raise FileNotFoundError(f"HTML file not found: {self.html_file}")

        logger.info("PDF Converter initialized successfully")
        logger.info(f"  HTML File: {self.html_file}")
        logger.info(f"  PDF Output: {self.output_pdf}")
        logger.info(f"  Base Directory: {self.base_dir}")

    def _get_perfect_code_css(self) -> str:
        """Return the renderer's targeted code CSS.

        Retained for parity with the historical class surface. Note this string
        is intentionally distinct from :meth:`PdfPreprocessor.get_perfect_code_css`
        (different font ordering, padding, and a paged ``@page`` header/footer).
        """
        return """
        /* TARGETED MONOSPACE FIXES - PRESERVE ORIGINAL OASIS CSS */
        
        /* Code elements - monospace font only */
        code, pre, .sourceCode, .highlight, tt, kbd, samp {
            font-family: "Courier New", "DejaVu Sans Mono", "Liberation Mono", "Consolas", "Monaco", monospace !important;
            font-weight: normal !important;
            font-style: normal !important;
            letter-spacing: 0 !important;
            word-spacing: 0 !important;
        }
        
        /* Inline code styling */
        code {
            font-size: 0.9em !important;
            background-color: #f5f5f5 !important;
            border: 1px solid #ddd !important;
            border-radius: 2px !important;
            padding: 1px 3px !important;
            white-space: nowrap !important;
        }
        
        /* Block code styling */
        pre {
            font-size: 0.85em !important;
            line-height: 1.2 !important;
            background-color: #f8f8f8 !important;
            border: 1px solid #ccc !important;
            border-radius: 4px !important;
            padding: 8pt !important;
            margin: 6pt 0 !important;
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
            padding: 8pt !important;
            margin: 6pt 0 !important;
        }
        
        /* Language-specific code blocks */
        .json, .xml, .yaml, .bash, .shell, .python, .javascript, .http {
            font-size: 0.85em !important;
            line-height: 1.2 !important;
            background-color: #f8f8f8 !important;
            border: 1px solid #ccc !important;
            padding: 8pt !important;
            white-space: pre-wrap !important;
        }
        
        /* Code in tables */
        table code, td code, th code {
            font-size: 0.8em !important;
            white-space: nowrap !important;
        }
        
        /* PDF-specific code improvements */
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
        
        /* Page setup for portrait with wider margins */
        @page {
            size: A4 portrait;
            margin: 2.5cm 2cm 2.5cm 2cm;
            
            @top-center {
                content: string(title);
                font-size: 10pt;
                color: #666;
            }
            
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        /* Title string for header */
        h1:first-of-type, h1big:first-of-type {
            string-set: title content();
        }
        
        /* Minimal PDF improvements that don't override OASIS styles */
        h1, h1big, h2, h3, h4, h5, h6 {
            page-break-after: avoid !important;
        }
        
        /* No page breaks in inappropriate places */
        .no-page-break {
            page-break-inside: avoid !important;
        }
        """

    def _preprocess_html(self, html_content: str) -> str:
        """Tag code blocks and headings to improve PDF structure; return HTML.

        Retained for parity with the historical class surface.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Ensure all code blocks have proper classes
        for pre in soup.find_all('pre'):
            if not pre.get('class'):
                pre['class'] = ['code-block']

        # Fix any code elements without proper parent structure
        for code in soup.find_all('code'):
            if code.parent and code.parent.name != 'pre':
                # This is inline code
                if not code.get('class'):
                    code['class'] = ['inline-code']

        # Ensure proper line breaks in code blocks
        for pre in soup.find_all('pre'):
            # Make sure pre blocks preserve whitespace
            if pre.string:
                # Replace any problematic whitespace
                content = str(pre.string)
                pre.string.replace_with(content)

        # Add no-page-break class to important elements
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h1big']):
            classes = heading.get('class', [])
            classes.append('no-page-break')
            heading['class'] = classes

        return str(soup)

    def build_command(self, html_file_path: str) -> list[str]:
        """Return the exact wkhtmltopdf argument vector for this conversion.

        Isolated from execution so the command can be asserted token-for-token
        without invoking wkhtmltopdf. The tokens and their order are contractual.
        """
        return [
            'wkhtmltopdf',
            '--page-size', 'A4',
            '--orientation', 'Portrait',
            '--margin-top', '25mm',
            '--margin-right', '20mm',
            '--margin-bottom', '25mm',
            '--margin-left', '20mm',
            '--header-spacing', '6',
            '--header-font-size', '10',
            '--header-center', 'Common Security Advisory Framework Version 2.1',
            '--footer-line',
            '--footer-spacing', '4',
            '--footer-left', str(self.html_file.name),
            '--footer-center', 'Copyright © OASIS Open 2025. All Rights Reserved.',
            '--footer-right', '[date] - Page [page] of [topage]',
            '--footer-font-size', '8',
            '--footer-font-name', 'Times',
            '--no-outline',
            '--print-media-type',
            '--enable-local-file-access',
            '--load-error-handling', 'ignore',
            '--load-media-error-handling', 'ignore',
            html_file_path,
            str(self.output_pdf)
        ]

    def _convert_to_pdf(self, html_file_path: str) -> None:
        """Run wkhtmltopdf on ``html_file_path``; re-raise on failure.

        Captures wkhtmltopdf's output for diagnostics and logs any stderr at
        debug level; a non-zero exit is logged with stdout/stderr and re-raised.
        """
        logger.info("Converting HTML to PDF with wkhtmltopdf...")

        try:
            # Configure wkhtmltopdf command with document-specific settings
            cmd = self.build_command(html_file_path)

            logger.info("Executing PDF conversion with wkhtmltopdf")
            logger.debug(f"Command: {' '.join(cmd)}")

            # Execute wkhtmltopdf conversion
            result = self._run_subprocess(cmd, capture=True)

            if result.stderr:
                logger.debug(f"wkhtmltopdf output: {result.stderr}")

            logger.info("PDF conversion completed successfully")

        except subprocess.CalledProcessError as e:
            logger.error(f"wkhtmltopdf failed with exit code {e.returncode}")
            logger.error(f"stderr: {e.stderr}")
            logger.error(f"stdout: {e.stdout}")
            raise
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise

    def convert(self) -> None:
        """Render the HTML to PDF and verify the output file was created.

        Raises :class:`RuntimeError` if wkhtmltopdf reports success but the PDF
        is absent.
        """
        try:
            logger.info("Starting HTML to PDF conversion process")
            logger.info(f"Source HTML: {self.html_file}")

            # Execute PDF conversion
            self._convert_to_pdf(str(self.html_file))

            # Verify successful conversion
            if self.output_pdf.exists():
                size = self.output_pdf.stat().st_size
                logger.info(f"PDF generated successfully: {self.output_pdf} ({size:,} bytes)")
            else:
                raise RuntimeError("PDF file was not created successfully")

        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise

    def run(self) -> None:
        """Execute the rendering stage (alias for :meth:`convert`)."""
        self.convert()


def main() -> None:
    """CLI entry point: ``step_2_convert_html_to_pdf.py <html_file> [-o OUT] ...``.

    Preserves the original contract: ``-o/--output`` (default: input with a
    ``.pdf`` suffix), ``--base-dir``, ``-v/--verbose``; exits non-zero on failure.
    """
    parser = argparse.ArgumentParser(
        description="Convert HTML to PDF with enhanced code block formatting",
        epilog="This tool preserves original document styling while optimizing code blocks for PDF output."
    )

    parser.add_argument(
        "html_file",
        help="Path to the HTML file to convert"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output PDF file path (default: same as HTML with .pdf extension)"
    )

    parser.add_argument(
        "--base-dir",
        help="Base directory for resolving relative URLs (default: HTML file directory)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    PipelineStep.configure_logging(level=log_level, log_file="pdf_conversion.log")

    # Determine output file
    if args.output:
        output_pdf = args.output
    else:
        html_path = Path(args.html_file)
        output_pdf = html_path.with_suffix('.pdf')

    try:
        # Create converter and run
        converter = PdfRenderer(
            html_file=args.html_file,
            output_pdf=output_pdf,
            base_dir=args.base_dir
        )

        converter.convert()

        print("PDF conversion completed successfully")
        print(f"Output: {output_pdf}")

    except Exception as e:
        print(f"PDF conversion failed: {str(e)}")
        logger.error(f"Conversion failed", exc_info=True)
        sys.exit(1)
