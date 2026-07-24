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

# Publication quality: how OASIS validates and audits your specification

**Author: Michael Coletta, Technical Advisor, OASIS Open**

This is the guide for TC editors and chairs. It explains what happens to a
work-product package between "the TC is ready to vote" and "the publication
is live and verified on docs.oasis-open.org", and what your TC can run
yourself, today, to make that path a straight line.

There are two layers of quality control, and you own the first one.

![How the two layers dovetail](assets/architecture/validation-audit-dovetail.png?v=164)

## The two layers

**Layer 1 is validation: the acceptance criteria, run as code.** A single
Python file, [`pub-check/oasis_pub_check.py`](pub-check/),
runs the acceptance checks (a set that grows; `--list-checks` reports the live
count, and [CHECKS.md](pub-check/CHECKS.md) is the generated inventory)
against your package: the files you are about to submit, exactly as you
would submit them. Every
condition is reported; one that does not apply to your package's track, or
whose prerequisite is absent, reports NA with the reason. It needs no
configuration because every expectation is derived from the package itself:
its own front matter, its own CSS, its own schema `$id`s, its own directory
path. It sees only the package and never touches the live site.

You run this layer. Put it in your repository's CI, or run it by hand before
the TC votes. A package that exits 0 is publication-clean: the vote happens
on a document that will not bounce back for filename fixes, dead anchors, or
stale front matter.

**Layer 2 is the publication audit.** When TC Administration publishes your
package, the publication event itself is audited: 15 mandatory gates, each
requiring recorded evidence, covering the things no package-level tool can
see:

- byte identity between the live site and the repository
- the rendering against your TC's own precedent
- the chairs in the front matter against the live roster
- every directory index in the chain
- all four announcement channels at their destinations

An independent adversarial verifier, briefed to refute the publication
rather than confirm it, must pass before the audit closes.

**The dovetail.** Step 4b of the intake checklist is: re-run oasis-pub-check, on
our side, with the identical code, and triage every finding. Your entire
98-check validation layer plugs into the audit as one step. That is the
point of sharing the tool: both sides run the same code, so acceptance is
mechanical on both ends instead of trusted on either. Your green run
predicts our green run but does not substitute for it.

![The OASIS publication quality stack](assets/architecture/two-layer-stack.png?v=164)

## Layer 1: the checks

Every check exists because a real publication went wrong in that specific
way:

- a `TODO: add the link.` that shipped and stayed live for years
- a lowercase citation that 404ed on the case-sensitive host
- a PDF rendered from an older draft than the HTML beside it
- a self-referential symlink that a deploy materialized into 41 nested
  directories

The gate is the accumulated record of those correction rounds, plus the
publication pipeline's own lint registry, calibrated against a 13-package
regression corpus of real submissions in their original received form.

The checks group into six areas:

![pub-check validation flow](assets/gate.png?v=164)

| Area | Checks | What it protects |
|---|---|---|
| Naming and stages | 16 | stage tokens per the current [Naming Directives](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html), version directories, delivery filenames, live revision collisions |
| Front matter and links | 22 | This/Latest stage URL blocks, internal anchors, cited-but-not-shipped files, dead mail addresses, link-target mismatches |
| Content residue | 11 | editor TODOs, placeholder sections, stale pandoc headers, working titles |
| Rendering and sync | 24 | PDF built from the same revision as the HTML, embedded fonts vs the package's own CSS, image policy, Word render fidelity |
| Template and policy | 9 | required front-matter sections, the [TC Process](https://www.oasis-open.org/policies-guidelines/tc-process/) Conformance requirement, RFC 2119/8174 citation |
| Package hygiene | 16 | junk files, recursive symlinks, schema `$id` vs publish path, manifest sha256, ODT source integrity |

Every finding carries a severity. **BLOCKER** means the package cannot
publish until it is fixed (exit 1). **WARN** means publishable, flagged for
the record, and often a must-fix before a later stage. **INFO** is recorded,
no action required.

The full catalog, one row per condition with the exact value the tool pulls
and what it compares that value against, is in
[`pub-check/CHECKS.md`](pub-check/CHECKS.md), the acceptance criteria as a
document. It is generated from the
tool's own condition registry, so it cannot drift from the implementation;
`--list-checks` asserts the counts from the code every time it runs.

The gate is track-aware, because the input formats are many and various
while the output contract is fixed. Markdown-authored packages get the
markdown checks; DOCX-native packages (KMIP and PKCS#11 style) skip those
and gain Word render-fidelity checks instead; ODT-authored packages ship
the `.odt` as the authoritative source (the OpenDocument TC publishes from
the format it defines); packages authored in other formats (DocBook/XML,
LaTeX) receive the full format-agnostic output and package suites. The bar
is always the output: conformant HTML and PDF, with the
authoritative source alongside, at the canonical URLs.

## Layer 2: the 15 audit gates

The publication audit is recorded as a machine-validated JSON record; the
human-readable report is rendered from it. The verdict is computed from the
gate results and findings, never asserted by the auditor. These are the
gates, in the order they appear in every audit record:

| Gate | What it verifies |
|---|---|
| 1 | GitHub truth: the bytes on the live site equal the pushed repository HEAD |
| 1a | Live equals GitHub: any HTML difference (for example CDN rewrites) is diffed and classified |
| 2 | Render class vs precedent: the rendering matches the TC's own prior publications, same toolchain, same look |
| 3 | Front matter vs reality: chairs and editors against the live roster, the companion documents, and the request ticket |
| 3a | Stage name per the current Naming Directives; no revision collision on the live site |
| 4 | Index chain: every directory listing from the TC root down to the stage directory lists the publication |
| 5 | Zip and manifest: the archive is byte-identical to the tree, no junk members, all extras present |
| 6a | The allmembers Invitation to Comment was delivered, verified at the destination |
| 6b | The TC's own community post is live |
| 6c | The TC's comment-facility community post is live |
| 6d | The public review is discoverable in the open-reviews feed |
| 6e | The www news post is live, when the stage warrants one |
| 6f | The TCADMIN ticket carries the complete verified-link record |
| 7 | Independent adversarial verifier: a fresh reviewer with a mandate to refute the publication. The audit is not done until this gate passes |
| 8 | Visual eyeball: the live cover page and directory listings, screenshotted and actually looked at |

Gates that do not apply to a given stage (a news post for an early-stage
draft, for example) are recorded NA with a reason; nothing is silently
skipped.

## The two reports your TC receives

Both layers produce a standard report. TC Administration renders both at
intake and files them to your TCADMIN ticket and to the TC's `_audit/`
record; your own run of the tool gives you the identical underlying data
(the findings, the exit code, and with `--json` the full per-condition
record), just not the formatted document:

- **The Validation Report** itemizes every condition: the condition
  verified, the value the tool pulled from your package, the value it was
  compared against, and the result. Nothing is truncated. A condition that
  could not be evaluated (no network, no `pdftotext`, no manifest shipped)
  reports NA, never a silent pass.
- **The Publication Audit Report** carries the 15-gate table with the
  recorded evidence for each gate, any findings with severity and impact,
  and the computed verdict. This one is a TC Administration operational
  record of the publication event; you receive it on your ticket.

## A worked example: OpenEoX EoX-Core v1.0 CSD01

The [`examples/eox-core-v1.0-csd01/`](examples/eox-core-v1.0-csd01/)
directory contains the real Validation Report for a real publication, the
[OpenEoX EoX-Core v1.0 CSD01](https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html)
of 13 July 2026, filed on
[TCADMIN-4725](https://issues.oasis-open.org/browse/TCADMIN-4725).

That publication is the argument for running Layer 1 yourself.
The TC's first release candidate carried 13 blockers: the same set the
manual intake review found by hand. The third release candidate ran clean,
was published, and its validation report shows zero blockers across all 92
conditions of the inventory in force at that publication, with 9 warnings
and 3 informational notes, every one triaged in
the report header. Two rows from the observed-vs-expected table give the
flavor:

| Check | Condition verified | Value pulled (observed) | Compared against | Result |
|---|---|---|---|---|
| stage-name | Stage token is a recognized current stage | stage_directory: csd01 | valid stage set: wd, csd, cs, cnd, cn, os, ps, psd, pn, pnd, errata | PASS |
| residue | No 'Will be filled in' placeholders (early-stage tolerated, must resolve before CS) | 'Will be filled in' placeholder present in markdown and in html | the phrase 'Will be filled in' must not occur | WARN x2 |

That WARN is the system working as intended: the TC shipped acknowledgment
placeholders deliberately at CSD stage, the tool recorded it, the triage
noted it must clear before CS, and nobody had to exchange an email about it.

## Running it yourself

```bash
# against a stage directory
python3 pub-check/oasis_pub_check.py openeox/eox-core/v1.0/csd01/

# against a submission zip
python3 pub-check/oasis_pub_check.py eox-core-1.0-csd-01-20260713-rc3.zip

# machine-readable
python3 pub-check/oasis_pub_check.py <target> --json

# the check inventory, asserted from the code itself
python3 pub-check/oasis_pub_check.py --list-checks

# write the release manifests (manifest.json + the Work Product
# Manifest File, <stem>-manifest.txt)
python3 pub-check/oasis_pub_check.py <target> --emit-manifest
```

Single file, Python 3.10+, standard library only. `poppler-utils`
(`pdftotext`, `pdffonts`) is optional and enables the PDF cross-checks. In
CI, the whole job is checkout, Python, one command:
[`.github/workflows/pub-check.yml`](.github/workflows/pub-check.yml) is the
complete working example.

If your build also emits a `manifest.json` conforming to
[`pub-check/manifest-schema.json`](pub-check/manifest-schema.json) (per-file
sha256 and role, the source commit, the tool versions), intake verification
of your package becomes mechanical: we can prove the files we received are
the files your build produced.

## What this changes for your TC

1. Add the one-command CI job, or run the tool by hand before the vote.
2. Fix blockers before the TC votes; the vote then approves a
   publication-clean package.
3. Ship the `--json` record (or the exit code) with your submission; TC
   Administration renders and files the formal Validation Report at intake.
4. TC Administration re-runs the identical gate at intake, publishes, audits
   the publication event, and files both reports to your ticket.

Questions, false positives, or checks you think are missing:
michael.coletta@oasis-open.org, or open an issue on
[OASIS-Docs/publication-assurance](https://github.com/OASIS-Docs/publication-assurance).
The check inventory grows as real correction rounds surface new failure
modes; the catalog and the advertised counts regenerate from the code, so
the documentation keeps pace with the tool by construction.

---

**The documentation set:** [Repository overview](README.md) · [The acceptance criteria tool](pub-check/README.md) · [The criteria catalog](pub-check/CHECKS.md) · [Worked example](examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](TRANSFORMS.md) · [Architecture diagrams](assets/architecture/README.md)
