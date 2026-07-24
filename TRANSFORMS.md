<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.

This document may be copied, published, and distributed to others without
restriction, provided it is reproduced verbatim and this notice is retained.
Derivative works of this document are not permitted without prior written
authorization from OASIS Open, other than translation into languages other
than English. This document is the canonical statement of the publication
acceptance criteria it describes; the accompanying software is separately
licensed under the Apache License 2.0 (see LICENSE at the repository root).
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# The transforms, without the Actions

**Author: Michael Coletta, Technical Advisor, OASIS Open**

The three GitHub Actions workflows in this repository are thin CI wrappers.
Each one wraps a small number of plain commands. This page lists those
commands so the transforms can be read and run locally
with no GitHub Actions involved.

Everything in the workflow YAML that is *not* listed below is CI plumbing:
repository checkout, venv creation, `chmod`, input validation, git
commit/push, and `touch`-based timestamp management. None of it affects the
document output.

## Map

| Workflow file | What it actually runs | Output |
|---|---|---|
| `step_1_format_md_and_convert_to_html.yml` | `prettier`, then `pandoc`, then one Python post-processor | `spec.html` |
| `step_2_convert_md_to_html_pdf_final.yml` | one Python HTML preprocessor, then `wkhtmltopdf` | `spec.pdf` |
| `step_3_create_zipfile.yml` | `zip` | `spec.zip` |

## Stage 1: Markdown to HTML

Three commands, in order:

```bash
# 1. Normalize the markdown in place
prettier --write spec.md

# 2. Base conversion (this is the exact pandoc invocation the pipeline uses)
pandoc spec.md \
  -f markdown+autolink_bare_uris+hard_line_breaks \
  -c https://docs.oasis-open.org/styles/markdown-styles-v1.7.3.css \
  -s --toc \
  --metadata title="<document title>" \
  -o temp_output.html

# 3. OASIS-specific HTML fix-ups (see list below)
python3 .github/src/step_1_markdown_to_html_converter_V3_0.py \
  path/to/spec.md "$(pwd)" path/to/dir --md-format --md-to-html
```

The Python post-processor (`_post_process_html` in
`.github/src/step_1_markdown_to_html_converter_V3_0.py`) is where the
OASIS-specific knowledge lives. It applies, in order:

1. Drops the pandoc-generated `<header>` block and stray `<nav>` TOC
   (the document carries its own Table of Contents section).
2. Injects a `<meta name="description">` derived from the abstract.
3. Removes any `<base href>` tag. A base href silently breaks
   fragment-only links (`#section`) in the TOC.
4. Enforces exactly one OASIS logo image, pointing at the canonical
   `https://docs.oasis-open.org/templates/OASISLogo-v3.0.png`.
5. Normalizes the top banner block (logo / title / stage lines).
6. Removes duplicate heading anchor IDs (pandoc emits duplicates for
   repeated heading text; only the first survives).
7. Rewrites same-document anchors so they work both as a local file and
   under the published `docs.oasis-open.org` URL.
8. Converts remaining plain-text URLs to `<a>` links.
9. Optionally localizes remote CSS and images next to the HTML
   (`HTML_LOCALIZE_CSS=1`).

## Stage 2: HTML to PDF

Two commands:

```bash
# 1. Inject targeted monospace/code-block CSS without touching the OASIS styles
python3 .github/src/fix_html_for_pdf.py spec.html -o spec_pdf.html

# 2. Render (exact flags used by the pipeline)
wkhtmltopdf \
  --page-size A4 --orientation Portrait \
  --margin-top 25mm --margin-right 20mm --margin-bottom 25mm --margin-left 20mm \
  --header-spacing 6 --header-font-size 10 \
  --header-center "<document title>" \
  --footer-line --footer-spacing 4 \
  --footer-left "spec.html" \
  --footer-center "Copyright © OASIS Open 2026. All Rights Reserved." \
  --footer-right "[date] - Page [page] of [topage]" \
  --footer-font-size 8 --footer-font-name Times \
  --no-outline --print-media-type \
  --enable-local-file-access \
  spec_pdf.html spec.pdf
```

A note on renderers: wkhtmltopdf is what this repository's workflows run, but
the production pipeline has since moved to headless Chrome print-to-PDF with
CSS Paged Media (an injected `@page` block supplies the running header and
footer natively) because plain pandoc-plus-wkhtmltopdf output was not adequate
for the requirement. wkhtmltopdf's limits, for anyone evaluating alternatives:
untagged PDF, no bookmarks/outline, no PDF/A conformance, and internal links
that depend on the anchor fix-ups from Stage 1. A toolchain that produces a
tagged PDF with a real outline (for example typst) improves on each of those
points.

## Stage 3: Package

```bash
cd path/to/stage-dir && zip -r ../spec-version-stage.zip .
```

The workflow additionally runs `touch -d "<date> 17:00:00 UTC"` across the
directory so every published file carries the publication date. That step is
release management: it changes file timestamps only.

Every defect class these transforms guard against (the lint series D1-D7 and the post-render assertions A1/A2) is also enforceable in a TC's own build before submission, via [oasis-pub-check](pub-check/): `python3 pub-check/oasis_pub_check.py <stage-dir>`.

---

**The documentation set:** [Repository overview](README.md) · [TC guide](PUBLICATION-QUALITY.md) · [The acceptance criteria tool](pub-check/README.md) · [The criteria catalog](pub-check/CHECKS.md) · [Worked example](examples/eox-core-v1.0-csd01/README.md) · [Architecture diagrams](assets/architecture/README.md)
