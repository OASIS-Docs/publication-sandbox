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

# pub-check: run the publication gate before you submit

**Author: Michael Coletta, Technical Advisor, OASIS Open**

`pub_check.py` is the TC-side version of the checks OASIS TC Administration
applies to a submitted work-product package before it goes to
`docs.oasis-open.org`. Run it in your own build and the review round-trip
disappears: what the TC votes on is already publication-clean.

Trust, but verify: TC Administration runs the identical gate on every
submission at intake, regardless of what the TC's own build reported. A green
run on your side predicts a green run on ours -- it never substitutes for it.
That is the point of sharing the tool: both sides run the same code, so
acceptance is mechanical on both ends instead of trusted on either.

Single file, Python 3.10+, standard library only. No configuration:
everything is derived from the package itself. 92 individual checks across
34 check classes -- `--list-checks` asserts the inventory from the code, so
the advertised numbers cannot drift from the implementation. The gate is the
union of the intake acceptance criteria and the publication pipeline's full
lint registry (lint D1-D7 and PDF assertions A1/A2, absorbed 15 July 2026),
validated by a 12-month retrospective over real submissions in their
original received form.

## Usage

```bash
# against a stage directory
python3 pub_check.py openeox/eox-core/v1.0/csd01/

# against a submission zip
python3 pub_check.py eox-core-1.0-csd-01-20260713-rc3.zip

# machine-readable
python3 pub_check.py <target> --json

# the check inventory, asserted from the code itself (source of the advertised numbers)
python3 pub_check.py --list-checks

# also write manifest.json (per-file sha256, source commit, tool versions)
python3 pub_check.py <target> --emit-manifest
```

Exit 0 means publishable (warnings allowed). Exit 1 means blockers.

## Provenance

Every check corresponds to a finding from a real publication correction
round: the OpenEoX EoX-Core RC1/RC2 reviews (July 2026), the prov-meta
v1.0 CSD01 editorial fixes (May 2026), the DMLex missing-artifact 404s
(June 2026), the UBL cross-version link mix-up (August 2025), the DMLex
case-sensitivity incident, and the OASIS template / TC Process
requirements (Conformance section, RFC 2119 key-word references, naming
directives).

The DOCX-native track and its checks (generator, vml-fallback, asset-refs,
symlinks, HTML-cover front matter) come from the KMIP v3.0 csd02 publication
audit of 15 July 2026: the anchor check found three dangling bookmarks in the
live publication that two human audit passes had left unvalidated, and the
same day's cleanup removed 41 levels of directory recursion that a single
self-referential symlink in the csd01 package had materialized into on deploy.

Regression corpus (all packages as published on docs.oasis-open.org,
except RC1 which is the known-bad submission candidate):

| Package | Result |
|---|---|
| CSAF v2.0 csd01 | 2 blockers: a genuine shipped defect ("TODO: add the link.", line 354, still live) |
| CSAF v2.0 csd02, cs01, cs02, cs03, os, errata01 csd01, errata01 os | publishable |
| CSAF v2.1 csd01 | publishable |
| EoX-Core v1.0 csd01 RC3 (published) | publishable |
| EoX-Core v1.0 csd01 RC1 (known bad) | 13 blockers, matching the manual review |
| KMIP Spec v3.0 csd02 (DOCX-native, published) | publishable; 2 warnings = real dangling TOC bookmarks inherited from the source DOCX |
| KMIP Profiles v3.0 csd02 (DOCX-native, published) | publishable; warnings include the inherited #RFC8174 dangler |

## The checks

| Check | Severity | What it catches |
|---|---|---|
| version-naming | BLOCKER/WARN | Version directory not vN.N; a delivery filename embedding a DIFFERENT version than the publish path (stale-rename tell); stem missing the version segment. |
| revision-collision | WARN/INFO | The submission's stage already published live for this version (a new submission must increment the revision: the KMIP 'csd01 since 2024' scar), plus an INFO list of the version's live stages. Network-derived; PUB_CHECK_OFFLINE=1 skips. |
| stage-name | BLOCKER | Retired/invalid stage tokens (`csprd`, `cos`, `csdpr`, ...). A document in public review keeps its stage name. |
| filenames | BLOCKER | Delivery items not named `<base>-<stage>.md/.html/.pdf`; `draft`/`tmp`/`rc` tokens in shipped filenames. |
| front-matter | BLOCKER/WARN | This-Stage URLs that do not match the version/stage path or point at files not in the package; Latest-Stage URLs that carry a stage segment; URLs declaring a different version (stale-draft tell). |
| residue | BLOCKER/WARN | `TODO(...)`, `tbd` placeholder sections; `Will be filled in ...` (warn at CSD, must clear before CS). |
| html-residue | BLOCKER | Absorbed from publisher-toolkit lint_html.py: duplicate title `<h1>` (D1, double title on the PDF cover), stale pandoc `title-block-header` (D2), leaked `/home/runner` CI paths (D3). The shared workflows produce these; the gate catches them at intake too. |
| fence-collapse | BLOCKER | From publisher-toolkit preprocess_md.py (D6): an opening code fence with trailing text in its info string collapses the whole block to inline code under pandoc. Calibration: fires exactly 28 times on the as-submitted DPS prov-meta source, matching the May 2026 incident count. |
| image-policy | BLOCKER/WARN | From publisher-toolkit inline_images.py (D7): SVGs carrying `<script>`, `on*=` handlers, or external refs (active content, refused on the host); empty/absolute/traversal `img src`; `srcset`/`<picture>` (pipeline refuses); the 2MB/5MB inlining caps as warnings. |
| pdf-cover | BLOCKER | From publisher-toolkit step_2 assertions: A1 title appearing more than once on the PDF cover page (stale header residue baked into the render); A2 `/home/runner` CI paths in the PDF text. Needs `pdftotext`; silent skip without it. |
| html-title | BLOCKER | Working residue in the HTML `<title>` (`- tmp`, `draft`). |
| html-anchors | BLOCKER | Internal `#fragment` links with no matching anchor. |
| md-links | BLOCKER/WARN | Bare URL running into `.\` with no space (pandoc autolink pulls the period and backslash into the href); `[url](url)` dual links. |
| schema-id | BLOCKER | JSON schema `$id` that disagrees with the file's publish path (implementers get a 404). |
| pdf-sync | BLOCKER | PDF front matter missing the canonical this-stage URL or citing a different version: the PDF was rendered from an older draft. Unreadable PDF is a blocker. Needs `pdftotext` on PATH; warns if absent. |
| junk-files | BLOCKER | `.DS_Store`, `__MACOSX/`, `Thumbs.db`, editor backups, `.git/` inside the package. |
| case | BLOCKER/WARN | Mixed-case filenames or mixed-case `docs.oasis-open.org` paths: the publication host is case-sensitive and canonical paths are lowercase, so lowercase citations 404. |
| dead-lists | BLOCKER/WARN | Mail addresses at `lists.oasis-open.org` (mail to them fails silently; comments go through the Higher Logic comment facility now). |
| rfc-keywords | BLOCKER/WARN | Normative key words (MUST/SHOULD/...) used without citing RFC 2119; RFC 8174 missing gets a warning. |
| previous-stage | BLOCKER | csd02 and later must cite the previous stage's URLs; an empty or N/A Previous-Stage block on a second-or-later stage means stale front matter. |
| date-sync | BLOCKER/WARN | Front-matter date in the markdown absent from the HTML (rendered from a different revision); copyright year not matching the document date year. |
| logo | WARN | Logo not the canonical `templates/OASISLogo-v3.0.png`. |
| manifest | BLOCKER/INFO | If `manifest.json` is present, every listed sha256 must match the file on disk. |
| template | BLOCKER/WARN | Required front-matter sections present (This/Previous/Latest stage, TC, Chairs, Editors, Abstract) and in template order; Conformance section present (TC Process requirement). |
| template-css | BLOCKER/WARN/INFO | HTML must carry a stylesheet; canonical is the markdown-styles CSS. A spec shipping its own CSS is noted; a non-template font family is flagged. |
| package-refs | BLOCKER | Files the document cites under its own stage path that are not in the package (they 404 on publication). |
| link-mismatch | BLOCKER | Visible URL and link target disagree (classic rename artifact). |
| double-slash | BLOCKER | `//` inside a relative path; the CDN 404s it. |
| cover-hr | WARN | Horizontal rule between logo and title (renders as a blank first PDF page in the OASIS HTML-to-PDF path). |
| symlinks | BLOCKER | A symlink pointing at its own ancestor: deploys materialize symlinks (`rsync -L`, `s3 sync --follow-symlinks`), so it expands into unbounded directory recursion on the CDN origin (KMIP csd01 shipped 41 nested levels from one `x -> .`). |
| generator | BLOCKER | DOCX-native only: HTML `Generator` meta is not Microsoft Word. A LibreOffice/other render differs in kind from the TC's precedent and is a re-do, not a publication. |
| vml-fallback | BLOCKER | DOCX-native only: a `v:imagedata` with no paired `<![if !vml]><img>` fallback. VML-only images are invisible in every modern browser (the cover-logo class, shipped live twice). |
| asset-refs | BLOCKER | DOCX-native only: a relative `src`/`href` the HTML references (`.fld/` images, siblings) that is not in the package; it 404s on publication. Image refs escape link-only sweeps. |
| pdf-fonts | WARN/INFO | PDF embedded fonts vs the font families the package's own CSS declares (the CSS is the typography authority for a publication). Divergence is a finding, not a blocker. Needs poppler's `pdffonts`; skips gracefully without it or when the package declares no local font authority. |

Residue, key-word and link checks ignore fenced code blocks and `<pre>/<code>`
content, so schemas and examples containing `tbd` or bare URLs do not
false-positive (relevant for CSAF- and SARIF-sized documents).

## The manifest contract

If the package ships a `manifest.json` conforming to
[`manifest-schema.json`](manifest-schema.json), the intake side can verify
the whole package mechanically: per-file sha256, the source commit the
artifacts were built from, and the tool versions that built them. Emit it
from your own toolchain, or with `--emit-manifest`. Minimal shape:

```json
{
  "version": "v1.0",
  "stage": "csd01",
  "source": { "repo": "oasis-tcs/openeox", "commit": "<sha>", "tag": "<release tag>" },
  "tools": { "pandoc": "pandoc 3.8.2.1", "typst": "typst 0.15.0" },
  "items": [
    { "path": "eox-core-v1.0-csd01.md", "role": "authoritative", "sha256": "...", "bytes": 70555 }
  ]
}
```

Roles: `authoritative`, `delivery`, `schema`, `example`, `other`.

## CI

`.github/workflows/pub-check.yml` in this repository shows the whole CI
story: checkout, Python, `apt-get install poppler-utils` for the optional
PDF cross-check, then one command. There is deliberately nothing else in it.
A makefile target works just as well:

```make
.PHONY: pub-check
pub-check:
	python3 pub_check.py ../share/  # or your stage dir
```

## Scope and track detection

The bar is the output, not the input: every publication lands as conformant
HTML and PDF, with the authoritative source alongside, at the canonical URLs.
pub-check validates that bar. The full output suite (HTML checks: title,
anchors, residue, image policy, asset refs, rendered front-matter blocks;
PDF checks: source sync, cover assertions, fonts; package checks: naming,
versioning, stage, collision, hygiene, symlinks, schemas, manifest) runs on
EVERY package regardless of how it was authored. Source-format checks are
add-ons applied to whatever the package carries:

- **Markdown source present**: the markdown add-ons (front-matter cross-check,
  autolink trap, fence-collapse, template sections, correction classes).
- **Word source present, no markdown** (KMIP, PKCS#11 style): the Word
  render-fidelity add-ons (Microsoft Word generator, VML image fallbacks),
  with the front-matter blocks parsed from the rendered HTML cover. Dangling
  internal anchors report as warnings here: they are source-DOCX artifacts
  whose fix path is the TC's next revision, not the render.
- **Neither** (DocBook/XML, LaTeX, and other TC-rendered formats): the full
  output and package suites still run; a warning asks for the authoritative
  source to travel with the renderings.

Other authoring formats exist in the published corpus -- DocBook/XML (UBL,
Electronic Court Filing; the XML is often the authoritative artifact), LaTeX
(Virtio), and more. Packages in those formats receive the format-agnostic
checks (stage naming, version-naming, revision collision, case, hygiene,
symlinks, dead-lists, link and packaging checks); dedicated track awareness
for them is roadmap, calibrated the same way the first two tracks were --
against the published corpus.

Repackaging or re-rendering is never suggested cross-track; render class is
judged against the TC's own publication precedent.
