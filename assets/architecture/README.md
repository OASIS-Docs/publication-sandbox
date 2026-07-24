# Publication quality architecture diagrams

Three diagrams on the OASIS design system (Poppins, ink `#0a2540`, accent
`#2248e5`), delivered as 2x PNGs.

## Subject

How the OASIS publication quality architecture's two layers dovetail:

- Layer 1, validation (pub-check), is mechanical and tool-side.
  `oasis_pub_check.py` runs the acceptance checks (`--list-checks` reports
  the live count). The TC runs it in its own CI before submission, and TC
  Administration re-runs the identical code at intake. It only ever sees the
  package files. Its output is the Validation Report, which lists every
  condition with the observed value the tool pulled set against the expected
  value it was compared to, shown in full (rendered landscape so the
  values stay legible).
- Layer 2, the publication audit, is human and adversarial, event-side. 15
  mandatory gates run against live ground truth the tool cannot see: byte
  identity, render class vs precedent, live roster, Naming Directives, index
  chain, zip integrity, four announcement channels, ticket record, an
  independent adversarial verifier, a literal visual eyeball. Every gate
  needs recorded evidence, and the verdict is computed from that record.
  Its output is the Publication Audit Report.
- The dovetail is intake checklist step 4b, which requires running
  oasis-pub-check and triaging every finding, so the whole validation layer
  plugs into the audit as one step. Both reports are filed to the TC's ticket
  and the internal `_audit/` directory.

The prose companion to these diagrams is
[../../PUBLICATION-QUALITY.md](../../PUBLICATION-QUALITY.md).

## Files

### `validation-audit-dovetail.png` (2800 x 1800, landscape)

Two swim lanes, TC side (Layer 1) and TC Administration side (Layer 2). The
shared `pub-check` engine sits in the seam between them with dovetail keys
seating into both lanes: the identical code running on both sides, the TC in
CI on the left, checklist step 4b on the right. The audit gates that need
live ground truth are laid out as a chip grid, the independent adversarial
verifier is called out separately, and both report artifacts flow down to
the shared TCADMIN ticket and `_audit/` record. Primary explainer figure for
TC editors and for TC Administration process documentation.

### `two-layer-stack.png` (1800 x 2200, portrait), slide summary

A vertical stack that reads bottom to top: package in, Layer 1 validation,
the step-4b dovetail joint, Layer 2 audit, published and verified
publication. Each layer carries a "what the tool sees" (Layer 1) versus
"what only a human or live check can see" (Layer 2) annotation panel. One
slide in a deck, or a sidebar summary next to the primary diagram.

### `nide-bridge.png` (2480 x 1280, landscape)

The *cross-tool* dovetail: how pub-check (OASIS intake) interoperates with
Stefan Hagen's `nide` (TC-side authoring). Two engine lanes with a shared
seam. The rules flow one way (OASIS authors `oasis.rules.yaml`, nide pulls it
via `extends: oasis`, both gates evaluate it), the package and its
`nide-manifest` flow the other (nide emits, pub-check hash-verifies the
delivered bytes). One rules file, one manifest, two gates: a green
`nide quality` run predicts a green intake. Distinct from the two diagrams
above, which show the *internal* dovetail of validation into the human audit.

---

**The documentation set:** [Repository overview](../../README.md) · [TC guide](../../PUBLICATION-QUALITY.md) · [The acceptance criteria tool](../../pub-check/README.md) · [The criteria catalog](../../pub-check/CHECKS.md) · [Worked example](../../examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](../../TRANSFORMS.md)
