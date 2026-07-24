<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.
This directory contains the quality record of an OASIS
publication, reproduced verbatim as a worked example.
-->

# Worked example: OpenEoX EoX-Core v1.0 CSD01

The Validation Report for
[OpenEoX Core Schema Version 1.0 CSD01](https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html),
published 13 July 2026 and filed on
[TCADMIN-4725](https://issues.oasis-open.org/browse/TCADMIN-4725).
This is the standard record every TC receives for every publication.

| File | What it is |
|---|---|
| `eox-core-v1.0-csd01-pub-check-validation-2026-07-16.md` / `.pdf` | The Validation Report: all 92 conditions, each with the value the tool pulled from the package set against the value it was compared to. Zero blockers; 9 warnings and 3 informational notes, triaged in the header. |

Running `oasis_pub_check.py` yourself gives you the
findings, the exit code, and with `--json` the full per-condition record
(the same conditions, observed values, and comparisons shown in this
report). The formatted report itself is rendered by TC Administration at
intake from that same data and filed to your ticket. Your run and ours
carry identical content; the rendering is ours.

The publication is also audited at the event level (15 mandatory gates:
byte identity, index chains, announcements, an independent adversarial
verifier); that Publication Audit Report is a TC Administration operational
record filed to the ticket. This example carries only the Validation Report.

The publication's history shows what the gate catches: the TC's first release
candidate carried 13 blockers, the same set the manual intake review found.
The third release candidate ran clean and was published.

This report is a record of one specific publication, carrying the
92-condition inventory in force when it was published. The acceptance
criteria grow as correction rounds surface new failure modes (the
current set is already larger); the criteria in force are always
[`pub-check/CHECKS.md`](../../pub-check/CHECKS.md), generated from the code.

---

**The documentation set:** [Repository overview](../../README.md) · [TC guide](../../PUBLICATION-QUALITY.md) · [The acceptance criteria tool](../../pub-check/README.md) · [The criteria catalog](../../pub-check/CHECKS.md) · [The pipeline, command by command](../../TRANSFORMS.md) · [Architecture diagrams](../../assets/architecture/README.md)
