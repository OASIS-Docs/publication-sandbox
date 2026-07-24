#!/bin/bash
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

# Exit immediately if a command exits with a non-zero status
set -e

# Directory containing the HTML file, provided as the first argument
DIR="$1"

# Ensure the directory exists
if [ -z "$DIR" ] || [ ! -d "$DIR" ]; then
  echo "Directory not specified or does not exist: $DIR"
  exit 1
fi

# Find the first HTML file in the directory
HTML_FILE=$(find "$DIR" -name '*.html' | head -n 1)

# Check if the HTML file was found
if [ -z "$HTML_FILE" ]; then
  echo "HTML file not found in directory: $DIR"
  exit 1
fi

echo "Found HTML file: $HTML_FILE"

# Define the output PDF file path by replacing .html with .pdf
PDF_FILE="${HTML_FILE%.html}.pdf"
echo "Output PDF file will be: $PDF_FILE"

# Run the wkhtmltopdf command to convert the HTML file to PDF
echo "Running wkhtmltopdf to convert HTML to PDF..."
# The --enable-local-file-access flag is crucial for allowing wkhtmltopdf
# to load local CSS and image files referenced in the HTML.
if wkhtmltopdf --enable-local-file-access "$HTML_FILE" "$PDF_FILE"; then
  echo "HTML to PDF conversion completed successfully"
else
  echo "HTML to PDF conversion failed"
  exit 1
fi
