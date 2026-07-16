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

"""Unit tests for the refactored PDF pipeline stages.

These tests pin the two things that must not drift silently: the exact
wkhtmltopdf argument vector produced by :class:`PdfRenderer` (token-for-token),
and the code-block CSS injection performed by :class:`PdfPreprocessor`. Neither
test requires wkhtmltopdf to be installed.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Make the pipeline package importable (src/ is this file's grandparent).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pdf_preprocessor import PdfPreprocessor
from pipeline.pdf_renderer import PdfRenderer


class TestPdfRendererCommand(unittest.TestCase):
    """The wkhtmltopdf command construction is contractual and must be stable."""

    def test_build_command_is_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "spec.html"
            html.write_text("<html></html>", encoding="utf-8")
            pdf = Path(tmp) / "spec.pdf"

            renderer = PdfRenderer(str(html), str(pdf))
            cmd = renderer.build_command(str(html.resolve()))

            expected = [
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
                '--footer-left', 'spec.html',
                '--footer-center', 'Copyright © OASIS Open 2025. All Rights Reserved.',
                '--footer-right', '[date] - Page [page] of [topage]',
                '--footer-font-size', '8',
                '--footer-font-name', 'Times',
                '--no-outline',
                '--print-media-type',
                '--enable-local-file-access',
                '--load-error-handling', 'ignore',
                '--load-media-error-handling', 'ignore',
                str(html.resolve()),
                str(pdf.resolve()),
            ]
            self.assertEqual(cmd, expected)


class TestPdfPreprocessor(unittest.TestCase):
    """The preprocessor injects the code CSS and tags bare code elements."""

    def test_css_injected_and_code_tagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.html"
            src.write_text(
                "<html><head></head><body>"
                "<pre>block</pre><p><code>x</code></p>"
                "</body></html>",
                encoding="utf-8",
            )
            out = Path(tmp) / "out.html"

            PdfPreprocessor(src, out).preprocess()
            result = out.read_text(encoding="utf-8")

            self.assertIn("TARGETED MONOSPACE FIXES", result)
            self.assertIn('class="code-block"', result)
            self.assertIn('class="inline-code"', result)


if __name__ == "__main__":
    unittest.main()
