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

# oasis-pub-check: run the OASIS publication acceptance criteria before you submit

**Author: Michael Coletta, Technical Advisor, OASIS Open**

![oasis-pub-check: the acceptance criteria](../assets/gate.png?v=98)

`oasis_pub_check.py` is the executable form of the publication acceptance
criteria: the TC-side version of the checks OASIS TC Administration
applies to a submitted work-product package before it goes to
`docs.oasis-open.org`. Run it yourself before you submit, and fix anything
it flags while the document is still in your hands.

TC Administration runs the same gate on every submission at intake. Both
sides run the same code, so a green run on your side predicts a green run at
intake.

The shape of the tool:

- Single file, Python 3.10+, standard library only. Nothing to install.
- No configuration. Every expectation is derived from the package itself:
  its own front matter, its own CSS, its own schema `$id`s, its own publish
  path.
- 165 individual checks across 55 check classes.
  `--list-checks` asserts the inventory from the code, so the advertised
  numbers cannot drift from the implementation.
- It combines the intake acceptance criteria with the publication
  pipeline's lint registry (D1-D7 and the PDF assertions A1/A2), checked
  against 12 months of submissions as received.

Three companion documents:

- [CHECKS.md](CHECKS.md): the per-condition catalog, one row per check with
  the value the tool pulls and what it compares that value against.
  Generated from the code's own condition registry by
  [render_checks_md.py](render_checks_md.py).
- [../PUBLICATION-QUALITY.md](../PUBLICATION-QUALITY.md): the TC-facing
  guide to the validation and audit layers.
- [../examples/eox-core-v1.0-csd01/](../examples/eox-core-v1.0-csd01/):
  the Validation Report from a publication.

## Usage

```bash
# against a stage directory
python3 oasis_pub_check.py openeox/eox-core/v1.0/csd01/

# against a submission zip
python3 oasis_pub_check.py eox-core-1.0-csd-01-20260713-rc3.zip

# machine-readable
python3 oasis_pub_check.py <target> --json

# the check inventory, asserted from the code itself (source of the advertised numbers)
python3 oasis_pub_check.py --list-checks

# write the release manifests: manifest.json (machine) and the
# <stem>-manifest.txt Work Product Manifest File (staff record)
python3 oasis_pub_check.py <target> --emit-manifest
```

Exit 0 means publishable (warnings allowed). Exit 1 means blockers.

## Where the checks come from

Each check comes from written OASIS policy (the TC Process, the Naming
Directives, the RFC 2119/8174 key-word rules) or from a correction round in
OASIS publication work across CSAF, KMIP, PKCS#11,
OpenEoX, NIEM, Akoma Ntoso and LegalDocML, DMLex, UBL, Electronic Court
Filing, STIX, OSLC, Virtio, DPS, ACAL, and OpenDocument, authored in
Markdown, Word, ODT, DocBook/XML, and LaTeX. The correction rounds behind
the checks include:

- an editor placeholder that went live and stayed for years
- a mixed-case citation that 404ed on the case-sensitive host
- a PDF rendered from an older draft than the HTML beside it
- front matter citing files that were never published
- a retired stage token in a published path
- dangling internal anchors that two human review passes had missed
- a self-referential symlink a deploy materialized into 41 nested directories

The template and TC Process requirements (the Conformance section, the RFC
2119/8174 key-word references, the Naming Directives) are enforced as
checks in the same set.

Calibration:

- a 13-package regression corpus of submissions as received, across
  multiple authoring tracks
- one release candidate whose 13 blockers match the manual intake review
- a 12-month retrospective over the year's intake, as received, which
  surfaced live defects on docs.oasis-open.org; those became checks too

New failure modes found in later correction rounds become new acceptance
criteria, and the catalog and advertised counts regenerate from the code
(`--list-checks` asserts them), so the criteria in force are always exactly
the ones the tool runs.

## The checks

Class-level summary; the full per-condition catalog with observed-vs-expected
detail is [CHECKS.md](CHECKS.md).

| Check | Severity | What it catches |
|---|---|---|
| version-naming | BLOCKER/WARN | Version directory not vN.N; a delivery filename embedding a DIFFERENT version than the publish path (stale-rename tell); stem missing the version segment. |
| revision-collision | WARN/INFO | The submission's stage already published live for this version (a new submission must increment the revision; one publication sat wrongly at csd01 for two years), plus an INFO list of the version's live stages. Network-derived; PUB_CHECK_OFFLINE=1 skips. |
| stage-name | BLOCKER | Retired/invalid stage tokens (`csprd`, `cos`, `csdpr`, ...). A document in public review keeps its stage name. |
| filenames | BLOCKER | Delivery items not named `<base>-<stage>.md/.html/.pdf`; `draft`/`tmp`/`rc` tokens in delivered filenames. |
| front-matter | BLOCKER/WARN | This-Stage URLs that do not match the version/stage path or point at files not in the package; Latest-Stage URLs that carry a stage segment; URLs declaring a different version (stale-draft tell). |
| residue | BLOCKER/WARN | `TODO(...)`, `tbd` placeholder sections; `Will be filled in ...` (warn at CSD, must clear before CS). |
| html-residue | BLOCKER | Absorbed from publisher-toolkit lint_html.py: duplicate title `<h1>` (D1, double title on the PDF cover), stale pandoc `title-block-header` (D2), leaked `/home/runner` CI paths (D3). The shared workflows produce these; the gate catches them at intake too. |
| fence-collapse | BLOCKER | From publisher-toolkit preprocess_md.py (D6): an opening code fence with trailing text in its info string collapses the whole block to inline code under pandoc. Calibration: fires exactly 28 times on one as-submitted source, matching that incident's manual count. |
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
| template-css | BLOCKER/WARN/INFO | HTML must carry a stylesheet; canonical is the markdown-styles CSS. A spec that carries its own CSS is noted; a non-template font family is flagged. |
| package-refs | BLOCKER | Files the document cites under its own stage path that are not in the package (they 404 on publication). |
| link-mismatch | BLOCKER | Visible URL and link target disagree (classic rename artifact). |
| double-slash | BLOCKER | `//` inside a relative path; the CDN 404s it. |
| cover-hr | WARN | Horizontal rule between logo and title (renders as a blank first PDF page in the OASIS HTML-to-PDF path). |
| symlinks | BLOCKER | A symlink pointing at its own ancestor: deploys materialize symlinks (`rsync -L`, `s3 sync --follow-symlinks`), so it expands into unbounded directory recursion on the CDN origin (KMIP csd01 produced 41 nested levels from one `x -> .`). |
| generator | BLOCKER | DOCX-native only: HTML `Generator` meta is not Microsoft Word. A LibreOffice/other render differs in kind from the TC's precedent and must be re-done before publication. |
| vml-fallback | BLOCKER | DOCX-native only: a `v:imagedata` with no paired `<![if !vml]><img>` fallback. VML-only images are invisible in every modern browser (the cover-logo class, published live twice). |
| asset-refs | BLOCKER | DOCX-native only: a relative `src`/`href` the HTML references (`.fld/` images, siblings) that is not in the package; it 404s on publication. Image refs escape link-only sweeps. |
| pdf-fonts | WARN/INFO | PDF embedded fonts vs the font families the package's own CSS declares (the CSS is the typography authority for a publication). Divergence is a non-blocking finding. Needs poppler's `pdffonts`; skips gracefully without it or when the package declares no local font authority. |

Residue, key-word and link checks ignore fenced code blocks and `<pre>/<code>`
content, so schemas and examples containing `tbd` or bare URLs do not
false-positive (relevant for CSAF- and SARIF-sized documents).

## The manifest contract

Every OASIS publication now includes two manifest artifacts, generated by the
same command on either side of the gate (`--emit-manifest`):

- `manifest.json`: the machine contract below, verified mechanically at
  intake.
- `<stem>-manifest.txt`: the Work Product Manifest File, the
  human-readable staff record published beside the release: bibliographic
  block, ZIP archive listing, and SHA-256 digests. This revives a
  long-standing OASIS Staff practice; the
  [OpenDocument releases](https://docs.oasis-open.org/office/OpenDocument/v1.4/csd01/OpenDocument-v1.4-csd01-manifest.txt)
  carry the precedent.

![The verification chain](../assets/chain.png?v=98)

If the package includes a `manifest.json` conforming to
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
PDF cross-check, then one command. There is nothing else in it. A makefile
target works just as well:

```make
.PHONY: pub-check
pub-check:
	python3 oasis_pub_check.py ../share/  # or your stage dir
```

## Scope and track detection

The gate measures the output. Every publication is conformant HTML and PDF,
with the authoritative source alongside, at the canonical URLs. The output
contract is the same regardless of input format. oasis-pub-check validates
that output. The full output suite (HTML checks: title,
anchors, residue, image policy, asset refs, rendered front-matter blocks;
PDF checks: source sync, cover assertions, fonts; package checks: naming,
versioning, stage, collision, hygiene, symlinks, schemas, manifest) runs on
EVERY package regardless of how it was authored. Source-format checks are
add-ons applied to whatever the package carries:

- Markdown source present: the markdown add-ons (front-matter cross-check,
  autolink trap, fence-collapse, template sections, correction classes).
- Word source present, no markdown (KMIP, PKCS#11 style): the Word
  render-fidelity add-ons (Microsoft Word generator, VML image fallbacks),
  with the front-matter blocks parsed from the rendered HTML cover. Dangling
  internal anchors report as warnings here: they are source-DOCX artifacts
  whose fix path is the TC's next revision.
- ODT source present, no markdown or Word: the `.odt` is the
  authoritative source and satisfies the source-travels contract (the
  OpenDocument TC publishes from the format it defines:
  [OpenDocument v1.4](https://docs.oasis-open.org/office/OpenDocument/v1.4/)).
  The full output and package suites run, the cover is parsed from the
  rendered HTML, and the ODT source-integrity checks verify the container
  itself: a valid OpenDocument archive, the declared mimetype, a parseable
  document body, and no embedded macros. Deeper render-fidelity add-ons
  grow the same way the existing tracks did, calibrated against the
  published corpus.
- None of the above (DocBook/XML, LaTeX, and other TC-rendered formats):
  the full output and package suites still run; a warning asks for the
  authoritative source to travel with the renderings.

Other authoring formats exist in the published corpus: DocBook/XML (UBL,
Electronic Court Filing; the XML is often the authoritative artifact), LaTeX
(Virtio), and more. Packages in those formats receive the format-agnostic
checks (stage naming, version-naming, revision collision, case, hygiene,
symlinks, dead-lists, link and packaging checks); dedicated track awareness
for them is roadmap, calibrated against the published corpus the same way
the first tracks were.

Repackaging or re-rendering is never suggested cross-track; render class is
judged against the TC's own publication precedent.

---

**The documentation set:** [Repository overview](../README.md) · [TC guide](../PUBLICATION-QUALITY.md) · [The criteria catalog](CHECKS.md) · [Worked example](../examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](../TRANSFORMS.md) · [Architecture diagrams](../assets/architecture/README.md)
