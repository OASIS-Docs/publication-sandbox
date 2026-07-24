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

# Function to sanitize paths by removing newlines and trimming whitespace
sanitize_path() {
  echo "$1" | tr -d '\n' | xargs
}

# Ensure that SYNC_PATH is provided
if [ -z "$SYNC_PATH" ]; then
  echo "Error: SYNC_PATH environment variable is not set."
  exit 1
fi

# Directory containing the Markdown file (Main directory)
MD_DIR=$(sanitize_path "$SYNC_PATH")
echo "Sanitized Directory containing Markdown file (MD_DIR): $MD_DIR"

# Base directory of the git repository (assuming the script is run from the repository root)
GIT_REPO_BASEDIR=$(pwd)
echo "Sanitized Base directory of git repository (GIT_REPO_BASEDIR): $GIT_REPO_BASEDIR"

# Ensure correct permissions for the directory and its contents
echo "Setting permissions for directory and files in $MD_DIR..."
chmod -R 775 "$MD_DIR"

# Find the first Markdown file in the directory (non-recursive)
MD_FILE=$(find "$MD_DIR" -maxdepth 1 -type f -name '*.md' | head -n 1)

if [ -z "$MD_FILE" ]; then
  echo "No Markdown file found in $MD_DIR"
  exit 1
else
  echo "Found Markdown file: $MD_FILE"
fi

# Define the path for the virtual environment
VENV_PATH="$GIT_REPO_BASEDIR/.github/src/venv"

# Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "Creating virtual environment at $VENV_PATH..."
  python3 -m venv "$VENV_PATH"
else
  echo "Virtual environment already exists at $VENV_PATH."
fi

# Activate the virtual environment
echo "Activating virtual environment at $VENV_PATH/bin/activate"
source "$VENV_PATH/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies (beautifulsoup4 and requests)
echo "Installing Python dependencies..."
pip install beautifulsoup4 requests

# (Optional) If you have a requirements.txt, use the following line instead:
# pip install -r requirements.txt

# Run the Python script to format the Markdown file
echo "Running Markdown formatting script (VERSION 3.0)..."
python3 ./.github/src/step_1_markdown_to_html_converter_V3_0.py "$MD_FILE" "$GIT_REPO_BASEDIR" "$MD_DIR" --md-format

# Run the Python script to convert the Markdown file to HTML
echo "Running Markdown to HTML conversion script..."
python3 ./.github/src/step_1_markdown_to_html_converter_V3_0.py "$MD_FILE" "$GIT_REPO_BASEDIR" "$MD_DIR" --md-to-html

echo "Markdown to HTML conversion completed successfully."
	
