<!--
Copyright 2025-2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

![OASIS Publication Assurance](assets/hero.png?v=98)

<p align="center">
  <a href="LICENSE"><img alt="Code: Apache-2.0" src="https://img.shields.io/badge/code-Apache--2.0-2c4a8a"></a>
  <a href="NOTICE"><img alt="Criteria prose: OASIS verbatim-only" src="https://img.shields.io/badge/criteria_prose-OASIS_verbatim--only-446CAA"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776ab">
  <img alt="Dependencies: stdlib only" src="https://img.shields.io/badge/gate_dependencies-stdlib_only-2f9e44">
  <img alt="Checks: 98 individual, 35 classes" src="https://img.shields.io/badge/checks-98_individual_%C2%B7_35_classes-f08c00">
  <img alt="Regression corpus: 13 packages" src="https://img.shields.io/badge/regression_corpus-13_packages-6741d9">
</p>

**Author: Michael Coletta, Technical Advisor, OASIS Open**

The public home of the machinery that publishes OASIS TC work products to
`docs.oasis-open.org`: the pipeline, the acceptance gate, and the publication
audit record, for any TC on any authoring track. The archived CSAF packages
under `csaf/` and `csaf-cvrf/` are the regression corpus, not the scope; the
worked example for the whole quality architecture is the real OpenEoX
publication in [examples/](examples/eox-core-v1.0-csd01/).

This repository contains:

1. **The publication acceptance criteria, executable**: [`pub-check/`](pub-check/)
   carries `oasis_pub_check.py`, the TC-side version of the acceptance
   criteria OASIS TC Administration applies to every submitted work product,
   and [CHECKS.md](pub-check/CHECKS.md), the full catalog generated from the
   tool's own registry. Run the tool before the TC votes: problems get fixed
   while the document is still yours, instead of being found at intake and
   sent back for correction and resubmission. This is the primary content of
   the repository.
2. **The open publication pipeline**: the machinery that turns a TC's source
   into the artifacts published at `docs.oasis-open.org`. OASIS generates
   from Markdown and from Word sources; [TRANSFORMS.md](TRANSFORMS.md)
   documents the Markdown path command by command. Whatever the source, the
   mandatory outputs are the same, and the gate performs additional
   format-specific checks on top of the output contract.

---

## oasis-pub-check: the acceptance criteria, run before you submit

![pub-check gate](assets/gate.png?v=98)

```bash
python3 pub-check/oasis_pub_check.py <stage-dir or submission.zip>   # exit 0 = publishable
python3 pub-check/oasis_pub_check.py <stage-dir> --emit-manifest     # + both release manifests
python3 pub-check/oasis_pub_check.py <stage-dir> --json              # machine-readable
```

oasis-pub-check is one Python file, uses only the standard library, and needs no
configuration. Every expectation is derived from the package itself (its own
front matter, its own CSS, its own schema `$id`s). The 98 individual checks
(35 check classes; `--list-checks` asserts the inventory from the code, and
the set grows) cover six areas:

- **Naming and stages**: stage tokens, version directories, filename
  conventions, live revision-collision probing, case sensitivity
- **Front matter and links**: This/Latest URL consistency, internal anchors,
  cited-but-not-shipped files, link-target mismatches, double-slash paths,
  dead `lists.oasis-open.org` addresses
- **Content residue**: editor placeholders, stale headers, working titles,
  the pandoc autolink trap
- **Rendering and sync**: PDF-vs-source sync, embedded fonts vs the
  package's own stylesheet, image policy, Word and ODT source fidelity
- **Template and policy**: required sections, the TC Process Conformance
  requirement, RFC 2119/8174 citation
- **Package hygiene**: junk files, symlinks, schema `$id` vs publish path,
  manifest sha256, ODT container integrity

Full table with severities: [pub-check/README.md](pub-check/README.md).

The criteria combine more than a year of real OASIS publication work
across CSAF, KMIP, PKCS#11, OpenEoX, NIEM, Akoma Ntoso and LegalDocML,
DMLex, UBL, Electronic Court Filing, STIX, OSLC, Virtio, DPS, ACAL, and
OpenDocument, in every authoring format those TCs use. Every check traces
to a real correction round somewhere in that body of work, the gate is
calibrated against a 13-package regression corpus of submissions in their
original received form (including one known-bad release candidate whose 13
blockers it reproduces exactly), and the set grows: each new failure mode
a correction round surfaces becomes a new acceptance criterion. Full
provenance: [pub-check/README.md](pub-check/README.md).

## Pipeline stages

![Pipeline](assets/pipeline.png?v=98)

Three GitHub Actions wrap six commands. Nothing else in the YAML affects the
output. [TRANSFORMS.md](TRANSFORMS.md) documents the exact commands, the nine
OASIS-specific HTML fix-ups, and the renderer's limits. Run them from the
Actions tab (each takes a stage directory and a date) or locally.

## Verification chain

![Verification chain](assets/chain.png?v=98)

If the package ships a `manifest.json` conforming to
[pub-check/manifest-schema.json](pub-check/manifest-schema.json) (per file:
sha256 and role; plus source commit and tool versions), OASIS intake can
verify it directly. The TC's build records what it produced, the gate checks it
against the criteria, and the manifest lets every later step verify both.

## Where the gate sits: validation and audit

![Validation and audit dovetail](assets/architecture/validation-audit-dovetail.png?v=98)

Two layers, one engine. The TC side runs oasis-pub-check in its own CI and owns
"the document is ready": all 98 conditions, each reported as the value the
tool pulled from the package set against the value it was compared to, in
full. TC Administration re-runs the identical code at intake (checklist
step 4b) and wraps it with the 15 mandatory audit gates only a human or a
live check can do: byte identity against the published site, render class
against the TC's own precedent, the live roster, directory index chains,
announcement channels, and an independent adversarial verifier.
Both reports are filed to the TC's ticket and the internal audit record.

**[PUBLICATION-QUALITY.md](PUBLICATION-QUALITY.md)** is the full guide for
TC editors and chairs: both layers, all 15 audit gates, the per-condition
catalog, and a worked example with the real Validation Report from a real publication
([examples/eox-core-v1.0-csd01/](examples/eox-core-v1.0-csd01/)).

![Publication quality stack](assets/architecture/two-layer-stack.png?v=98)

## CI

[`.github/workflows/pub-check.yml`](.github/workflows/pub-check.yml) defines
the CI path: checkout, Python, `poppler-utils` for the optional PDF checks,
one command. A one-line make target does the same:

```make
pub-check:
	python3 pub-check/oasis_pub_check.py path/to/stage-dir
```

## Repository structure

<details>
<summary>Full layout</summary>

```
publication-assurance/
├── pub-check/                       # The acceptance criteria (the primary content)
│   ├── oasis_pub_check.py           #   98 individual checks in 35 classes, stdlib only
│   ├── CHECKS.md                    #   the acceptance criteria catalog, generated from the code
│   ├── render_checks_md.py          #   the generator (keeps CHECKS.md in sync)
│   ├── manifest-schema.json         #   provenance manifest contract
│   └── README.md                    #   checks, severities, corpus (canonical criteria)
├── PUBLICATION-QUALITY.md           # The TC-facing guide: both layers, all gates
├── examples/eox-core-v1.0-csd01/    # The real Validation Report from a real publication
├── TRANSFORMS.md                    # The pipeline, command by command (canonical criteria)
├── assets/                          # The diagrams (PNG)
├── .github/
│   ├── src/                         # Pipeline source (pandoc + BeautifulSoup post-processing,
│   │                                #   HTML preprocessor, wkhtmltopdf renderer)
│   ├── scripts/                     # Shell entry points used by the workflows
│   ├── styles/                      # OASIS markdown-styles CSS lineage (v1.1 → v1.8.1)
│   └── workflows/                   # step_1 (MD→HTML), step_2 (HTML→PDF),
│                                    #   step_3 (zip), pub-check (the gate)
├── csaf/                            # Archived CSAF work products (v2.0 lineage, v2.1 csd01)
├── csaf-cvrf/                       # Archived CSAF-CVRF v1.2 work products
├── LICENSE                          # Apache-2.0 (software tier)
└── NOTICE                           # The three-tier IP statement
```

</details>

## Key technologies

Python 3.10+ · Pandoc · BeautifulSoup4 · Prettier · wkhtmltopdf (this repository)
/ headless Chrome + CSS Paged Media (current production) · GitHub Actions ·
poppler (`pdftotext`/`pdffonts`, optional, for the PDF cross-checks)

## License

Three tiers, stated precisely in [NOTICE](NOTICE):

1. **Software** (the document-processing pipeline under `.github/` and the
   pub-check gate under `pub-check/`) is licensed under the
   [Apache License, Version 2.0](LICENSE).
   Copyright OASIS Open. Authored by Michael Coletta, Technical Advisor to
   OASIS Open. Every source file carries an SPDX header.
2. **Acceptance-criteria documentation** (`TRANSFORMS.md`,
   `PUBLICATION-QUALITY.md`, `pub-check/README.md`, and the generated
   `pub-check/CHECKS.md`) is Copyright OASIS Open, All Rights Reserved:
   verbatim distribution is permitted with notices retained; derivative
   works require prior written authorization from OASIS Open. These
   documents are the canonical statement of the OASIS publication
   acceptance criteria.
3. **Archived OASIS specification packages** (`csaf/`, `csaf-cvrf/`) are
   OASIS Work Products and retain their own published OASIS copyright, IPR,
   and license notices. Nothing in this repository relicenses them.

The OASIS name and logo are trademarks of OASIS Open.

---

**Repository maintained by**: Michael Coletta, Technical Advisor, OASIS Open  
**Contact**: michael.coletta@oasis-open.org (OASIS TC Administration)  
**Documentation**: [PUBLICATION-QUALITY.md](PUBLICATION-QUALITY.md) for the whole quality architecture, [TRANSFORMS.md](TRANSFORMS.md) for the pipeline, [pub-check/](pub-check/) for the publication gate, individual specification folders for spec-level detail

---

**The documentation set:** [TC guide](PUBLICATION-QUALITY.md) · [The acceptance criteria tool](pub-check/README.md) · [The criteria catalog](pub-check/CHECKS.md) · [Worked example](examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](TRANSFORMS.md) · [Architecture diagrams](assets/architecture/README.md)
