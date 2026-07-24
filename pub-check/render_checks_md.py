#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Generate CHECKS.md, the OASIS publication acceptance criteria, from oasis_pub_check.py itself.

The catalog is rendered from the tool's own condition registry
(conditions_inventory(), which asserts the registry and the AST agree in
both directions), so the documentation cannot drift from the implementation.
Rerun after any change to the checks:

  python3 render_checks_md.py        # rewrites CHECKS.md next to this script
"""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

NOTICE = """\
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
GENERATED FILE: rendered from oasis_pub_check.py's condition registry by
render_checks_md.py. Edit the registry, not this file.
-->
"""

INTRO = """\
# The OASIS publication acceptance criteria

**Author: Michael Coletta, Technical Advisor, OASIS Open**

This is the acceptance criteria set for publication on docs.oasis-open.org,
executable: every individual condition `oasis_pub_check.py` verifies, one row per condition:
what is checked, the value the tool pulls from the package, what that value
is compared against, and the severity if the condition fails. This file is
GENERATED from the tool's own condition registry by `render_checks_md.py`,
and `--list-checks` asserts the registry against the implementation every
time it runs.

The gate is input-format agnostic. A TC generates its own outputs from
whatever source format it authors in (Markdown, Word, ODT, DocBook/XML,
LaTeX, anything else), and what the gate validates is the output contract:
conformant HTML and PDF, with the authoritative source travelling beside
them. Conditions marked `md`, `docx`, or `odt` in the Applies column are add-ons
that engage only when that source format is present in the package; every
other condition runs on every package regardless of how it was authored.
A package that includes only its outputs still gets the full output and
package suites.

{total} conditions across {classes} check classes.

## Legend

| Field | Values |
|---|---|
| Severity | **BLOCKER**: the package cannot publish until fixed (exit 1). **WARN**: publishable, flagged for the record, often a must-fix before a later stage. **INFO**: recorded, no action required. |
| Applies | **both**: every package, regardless of input format. **md** / **docx** / **odt**: add-on conditions that engage only when that source format is present; on any other package they report NA with the reason rather than passing silently. There is no closed list of input formats: DocBook/XML, LaTeX, and any other source are validated through the **both** conditions, with the cover parsed from the rendered HTML. |
| Requires | A package or environment feature (network, `pdftotext`, `pdffonts`, packaged schemas, a packaged manifest) without which the condition reports NA in the validation report rather than passing silently. |
"""

FOOTER = """\
---

Generated from `oasis_pub_check.py` by `render_checks_md.py`. The inventory is
asserted from the code: `python3 oasis_pub_check.py --list-checks` fails if the
registry and the implementation disagree in either direction.

**The documentation set:** [Repository overview](../README.md) · [TC guide](../PUBLICATION-QUALITY.md) · [The acceptance criteria tool](README.md) · [Worked example](../examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](../TRANSFORMS.md) · [Architecture diagrams](../assets/architecture/README.md)
"""

# One-line description per check class, keyed by class name. A new class
# added to pub_check.py without a line here fails the render (KeyError),
# which is the point: the catalog stays complete by construction.
CLASS_DESCRIPTIONS = {
    "asset-refs": "Relative files the HTML references must be included in the package.",
    "case": "The publication host is case-sensitive; canonical paths are lowercase.",
    "cover-hr": "A horizontal rule above the title opens the OASIS-rendered PDF with a blank page.",
    "date-sync": "The markdown, HTML, and copyright dates must describe the same revision.",
    "dead-lists": "Mail addresses at lists.oasis-open.org fail silently; comments go through Higher Logic.",
    "double-slash": "A double slash inside a relative path 404s on the CDN.",
    "fence-collapse": "An opening code fence with trailing text collapses the whole block under pandoc.",
    "filenames": "Delivery items are named for the published stage, one basename, all formats present.",
    "front-matter": "The This/Latest stage URL blocks must match the package's actual publish path.",
    "generator": "DOCX-native renders must come from Microsoft Word, matching the TC's precedent.",
    "html-anchors": "Every internal fragment link must resolve to an anchor in the document.",
    "html-residue": "Pipeline residue in the HTML: duplicate title H1, stale pandoc header, CI paths.",
    "html-title": "The HTML title element must be an actual document title with no working residue.",
    "image-policy": "Images must be self-contained, inert, and within the pipeline's size caps.",
    "junk-files": "OS and editor junk must not be in the package.",
    "link-mismatch": "A visible URL and its link target must agree.",
    "logo": "The cover logo should be the canonical OASIS template logo.",
    "manifest": "A packaged manifest.json must verify against the files on disk.",
    "md-links": "Markdown link forms that render wrong under pandoc autolinking.",
    "odt-integrity": "The ODT source must be a valid, macro-free OpenDocument container.",
    "package-refs": "Files the document cites under its own stage path must be included in the package.",
    "pdf-cover": "The rendered PDF cover must carry the title exactly once and no CI paths.",
    "pdf-fonts": "PDF embedded fonts are compared against the package's own CSS as typography authority.",
    "pdf-sync": "The PDF must be readable and rendered from the same revision as the rest of the package.",
    "previous-stage": "Second and later stages must cite the previous stage's URLs.",
    "residue": "Editor placeholders (TODO, tbd, 'Will be filled in') must not be present.",
    "revision-collision": "A new submission must not collide with a stage already live for the version.",
    "rfc-keywords": "Normative key words require the RFC 2119 (and 8174) citations.",
    "schema-id": "Every JSON schema's $id must agree with where the file actually publishes.",
    "stage-name": "The stage token must be a current, correctly numbered stage per the Naming Directives.",
    "symlinks": "Self-referential symlinks materialize into unbounded recursion on deploy.",
    "member-uri": "No OASIS member-only (Kavi) URI may be cited in a public work product (Naming Directives v1.7 s6.6).",
    "template": "The OASIS template's required front-matter sections, in order, plus Conformance.",
    "uri-chars": "No underscore may appear in a document (cover-page) URI (Naming Directives v1.7 s3).",
    "template-css": "The HTML must carry a stylesheet; the canonical CSS is the default expectation.",
    "version-naming": "The version directory and delivery filenames must agree on one vN.N(.N) version.",
    "artifact-naming": 'Non-document-identifier artifacts (schemas, images, WSDLs, codelists) should keep stable filenames across releases, not embed a stage/revision token.',
    "authors": "A Technical Report/Technical Report Draft must name one or more Authors on the cover page, distinct from a Committee Note's Editors listing.",
    "comment-resolution-log": 'A comment-resolution-log accompanying a CSD/CND public review, if present, must carry the exact Naming Directives basename (BLOCKER if misnamed); if the review has demonstrably concluded and no log-named file exists, that unexplained absence is flagged for confirmation (WARN). Near-miss detection folds away only hyphen/underscore word-joiners (not arbitrary punctuation) so unrelated files separated by other characters do not false-fire.',
    "conformance-structure": 'Standards Track Conformance section structure: top-level placement (not buried in an Annex/subsection), individually/uniquely numbered clauses per profile scope, and (CS->OS only) zero-tolerance clause-number-set preservation with a manual-review flag for wording-only changes.',
    "content-labels": 'Examples/Sample-<noun> headings should carry an explicit non-normative/informative content-type label (WARN); Appendix/Annex headings get the same structural test but only as a non-scoring advisory note.',
    "extension-conformance": 'Principal and Multi-Part named-part filename extensions should match a common OASIS publication rendering format, not an invented or proprietary token.',
    "extension-count": 'A delivery item must carry exactly one file extension after its document-identifier stem (BLOCKER, WARN at wd, case-folded at wd), matched only at a clean stem/extension boundary and never fooled by an empty dot-segment or an extra segment ahead of a blessed tar.gz/tar.bz2/tar.xz compound; every other package file (junk directories pruned) gets the same double-extension and missing-extension check as a non-blocking WARN advisory (Naming Directives v1.7 s4/s9).',
    "multi-part-naming": 'Multi-Part Work Product filenames must share one WP-abbrev/version-id (AC-NAMING-19) and, where the package is multi-part, insert a correctly formed, contiguously numbered -part<N>-<name> segment (AC-NAMING-20; Naming Directives v1.7 s4/s6.1), scoped to Standards Track CSD/CS/OS and Non-Standards Track CND/CN stage directories.',
    "name-chars": 'Every filename and directory name must stay within the sixty-four permitted characters; UNDERSCORE is a BLOCKER in an identifying (document-URI) name and a non-blocking WARN elsewhere. An empty identifying name is a BLOCKER, not silently accepted.',
    "normdef-refs": 'Every packaged normative schema/grammar/code file (Standards Track) must be referenced from the Work Product (TC Process 2.2.5).',
    "ns-segment": 'This/Latest-stage cover URIs must not reuse the reserved /ns/ path segment (namespace identifiers only); Previous-stage hits are WARN (inherited, immutable citation).',
    "public-review-metadata": 'Post-publication audit: a csd/cnd stage directory that underwent a TC public review must carry the [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber]-public-review-metadata.html companion file Project Administration is obligated to publish alongside it (Naming Directives v1.7 s5.2 / TC Handbook Naming).',
    "references-split": 'On a Standards Track work product, Normative and Informative References should be separately labeled, with no reference ID listed under both (handbook-WPQualityChecklist.txt, WARN).',
    "stage-token": "Second-and-later Previous-stage cover URIs should carry the document's own csd/cnd stage token (WARN if not: retired or mismatched, with a legacy pre-v1.7 verification caveat); Latest-stage cover URI filenames must never embed a stage-abbreviation/revision token at all (BLOCKER, matching-or-not is irrelevant). Token extraction is percent-decode-aware, prose-punctuation-tolerant, and splits on both '-' and '.' delimiters so a malformed filename that merges the version and stage with a period instead of a hyphen is still caught.",
    "title-oasis-prefix": "A Work Product title should not begin with 'OASIS' except on Project Administration's recommendation for special cases (Naming Directives v1.7 s7); BLOCKER on Standards Track, WARN on Non-Standards Track. Title identification shares one 0/1/2+ classification helper with check_html's D1 lint (no duplicated extraction logic), tolerates a <title>-only trailing brand suffix through a prefix-relationship singular-<h1> fallback rather than skipping a real violation, HTML-unescapes <h1> text before comparing it against the already-decoded <title>, and discloses in both the finding text and the observed evidence when the Standards/Non-Standards Track classification was itself a default (ambiguous stage prefix) rather than a confirmed read.",
    "title-version": "The cover-page title must incorporate the package's own Version identifier and, for Standards Track Work Products, compose it as '<name> Version <number>' (Naming Directives 5.1 / Section 7).",
    "uri-alias": 'No unauthorized URI aliasing within a stage/revision package: META-refresh, byte-identical duplicate files, or a redirect/URL-shortening domain citing a canonical OASIS resource (Naming Directives v1.7 s6.5).',
    "xml-namespace": 'Every namespace a packaged .xsd/.wsdl/.rng declares as its own must be a docs.oasis-open.org/[tc-shortname]/ns/xxxx URI (consistent scheme) or an allowlisted urn:.',
    "vml-fallback": "VML-only images in Word HTML renders are invisible in every modern browser.",
}


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    spec = importlib.util.spec_from_file_location("pub_check", HERE / "oasis_pub_check.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    inv = pc.conditions_inventory()   # raises on registry/AST drift

    classes = sorted({c["check"] for c in inv})
    counts = Counter(c["check"] for c in inv)
    lines = [NOTICE, INTRO.format(total=len(inv), classes=len(classes))]

    n = 0
    for cls in classes:
        lines.append(f"### {cls}\n")
        lines.append(CLASS_DESCRIPTIONS[cls] + "\n")
        lines.append("| # | Condition verified | Value pulled (observed) | "
                     "Compared against | Severity | Applies | Requires |")
        lines.append("|---|---|---|---|---|---|---|")
        for c in [c for c in inv if c["check"] == cls]:
            n += 1
            lines.append(
                f"| {n} | {esc(c['condition'])} | {esc(c['pulls'])} | "
                f"{esc(c['compares_to'])} | {c['severity']} | {c['applies']} | "
                f"{c.get('requires', '-')} |")
        lines.append("")

    lines.append(FOOTER)
    out = HERE / "CHECKS.md"
    out.write_text("\n".join(lines))

    text = out.read_text()
    rows = sum(1 for ln in text.splitlines()
               if ln.startswith("| ") and ln.split("|")[1].strip().isdigit())
    sections = sum(1 for ln in text.splitlines() if ln.startswith("### "))
    assert rows == len(inv), f"{rows} rows rendered, {len(inv)} in inventory"
    assert sections == len(classes), f"{sections} sections, {len(classes)} classes"
    print(f"wrote CHECKS.md: {rows} conditions, {sections} classes")


if __name__ == "__main__":
    main()
