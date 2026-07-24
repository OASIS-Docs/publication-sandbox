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

import os
import logging
import subprocess
from bs4 import BeautifulSoup
import argparse

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MarkdownToHtmlConverter:
    def __init__(self, md_file, output_file):
        self.md_file = md_file
        self.output_file = output_file
        self.meta_description = self.extract_meta_description(step=1)
        self.html_title = self.extract_html_title(step=1)
        self.css_file = 'https://docs.oasis-open.org/templates/css/markdown-styles-v1.7.3a.css'
        self.logo_url = "https://docs.oasis-open.org/templates/OASISLogo-v3.0.png"
        self.base_url = "https://docs.oasis-open.org/openc2/ap-hunt/v1.0/csd02/ap-hunt-v1.0-csd02.html"

    def extract_meta_description(self, step):
        logging.info(f"Step {step}: Extracting meta description from markdown file: {self.md_file}")
        try:
            with open(self.md_file, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.startswith('<!--') and 'description:' in line:
                        description = line.split('description:')[1].strip().strip('-->')
                        logging.info(f"Step {step}: Meta description extracted: {description}")
                        return description
            logging.warning(f"Step {step}: No meta description found in the markdown file.")
            return "-"
        except Exception as e:
            logging.error(f"Step {step}: Error extracting meta description: {e}")
            return "-"

    def extract_html_title(self, step):
        logging.info(f"Step {step}: Extracting HTML title from markdown file: {self.md_file}")
        try:
            with open(self.md_file, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.startswith('# '):  # Assuming the title is the first H1 element
                        title = line.strip('# ').strip()
                        logging.info(f"Step {step}: HTML title extracted: {title}")
                        return title
            logging.warning(f"Step {step}: No HTML title found in the markdown file.")
            return "-"
        except Exception as e:
            logging.error(f"Step {step}: Error extracting HTML title: {e}")
            return "-"

    def read_file(self, file_path):
        logging.info(f"Reading file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def write_file(self, file_path, content):
        logging.info(f"Writing to file: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def run_pandoc(self, step):
        logging.info(f"Step {step}: Running pandoc to convert markdown to HTML.")
        command = [
            'pandoc', self.md_file,
            '-f', 'markdown+autolink_bare_uris+hard_line_breaks',
            '-c', self.css_file,
            '--toc', '--toc-depth=5', '-s', '-o', 'temp_output.html',
            '--metadata', f'title={self.html_title}'
        ]
        logging.debug(f"Pandoc command: {' '.join(command)}")
        subprocess.run(command, check=True)
        logging.info(f"Step {step}: Pandoc command executed successfully.")

    def embed_css(self, html_content):
        logging.info("Embedding CSS into HTML content.")
        soup = BeautifulSoup(html_content, 'html.parser')
        for style in soup.find_all('style'):
            style.decompose()
        link_tag = soup.new_tag('link', rel='stylesheet', href=self.css_file)
        soup.head.append(link_tag)
        return str(soup)

    def convert_urls_to_hyperlinks(self, html_content):
        logging.info("Converting plain URLs to HTML hyperlinks.")
        soup = BeautifulSoup(html_content, 'html.parser')
        for p in soup.find_all('p'):
            new_content = []
            text_parts = p.decode_contents().split('<br/>')
            for part in text_parts:
                if 'http' in part:
                    words = part.split()
                    for i, word in enumerate(words):
                        if word.startswith('http'):
                            a_tag = soup.new_tag('a', href=word)
                            a_tag.string = word
                            new_content.append(str(a_tag))
                        else:
                            new_content.append(word)
                    new_content.append('<br/>')
                else:
                    new_content.append(part)
            p.clear()
            p.append(BeautifulSoup(' '.join(new_content), 'html.parser'))
        return str(soup)

    def post_process_html(self, html_content, step):
        logging.info(f"Step {step}: Starting post-processing of HTML content.")
        soup = BeautifulSoup(html_content, 'html.parser')
        if soup.header:
            soup.header.decompose()
            logging.info(f"Step {step}: Removed header from HTML content.")

        # Add meta description tag
        meta_tag = soup.new_tag('meta', attrs={'name': 'description', 'content': self.meta_description})
        soup.head.insert(0, meta_tag)
        logging.info(f"Step {step}: Added meta description tag.")

        # Add base URL tag
        base_tag = soup.new_tag('base', href=self.base_url)
        soup.head.insert(0, base_tag)
        logging.info(f"Step {step}: Added base URL tag.")

        # Add OASIS logo and horizontal rule
        logo_tag = soup.new_tag('img', src=self.logo_url, alt="OASIS Logo")
        soup.body.insert(0, logo_tag)
        hr_tag = soup.new_tag('hr', style="page-break-before: avoid")
        soup.body.insert(1, hr_tag)
        logging.info(f"Step {step}: Added OASIS logo and horizontal rule.")

        # Remove the extra OASIS logo within the <figure> tag
        for figure in soup.find_all('figure'):
            figure.decompose()
            logging.info(f"Step {step}: Removed extra OASIS logo within <figure> tag.")

        # Remove any duplicate or extra TOC elements
        if soup.nav:
            soup.nav.decompose()
            logging.info(f"Step {step}: Removed duplicate or extra TOC elements.")

        # Convert plain URLs to hyperlinks
        html_content_with_links = self.convert_urls_to_hyperlinks(str(soup))

        logging.info(f"Step {step}: Completed post-processing of HTML content.")
        return html_content_with_links

    def convert(self):
        try:
            step = 1
            logging.info(f"Step {step}: Starting conversion process.")
            self.run_pandoc(step=step)
            step += 1
            html_content = self.read_file('temp_output.html')
            logging.debug(f"Step {step}: Read generated HTML content from temp_output.html.")
            final_html = self.post_process_html(html_content, step=step)
            step += 1
            self.write_file(self.output_file, final_html)
            logging.info(f"Step {step}: HTML conversion and post-processing completed successfully.")
        except Exception as e:
            logging.error(f"An error occurred during conversion: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Markdown to HTML Converter')
    parser.add_argument('md_file', type=str, nargs='?', help='Path to the markdown file')
    parser.add_argument('--test', action='store_true', help='Run the script in test mode')

    args = parser.parse_args()

    if args.test:
        md_file = 'TOSCA-v2.0-csd06.md'
        output_file = md_file.replace('.md', '.html')
        logging.info(f'Running in test mode with md_file: {md_file} and output_file: {output_file}')
    else:
        if not args.md_file:
            parser.error('the following argument is required: md_file')
        md_file = args.md_file
        output_file = md_file.replace('.md', '.html')
        logging.info(f'Converting md_file: {md_file} to output_file: {output_file}')

    converter = MarkdownToHtmlConverter(md_file, output_file)
    converter.convert()

if __name__ == '__main__':
    main()