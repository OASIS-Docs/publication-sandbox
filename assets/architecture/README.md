# Publication Quality Architecture Diagrams

Hand-authored, self-contained SVGs (no external references, Arial/Helvetica, OASIS
palette with a single teal accent for the dovetail joint). Each SVG has a companion
PNG rendered at 2x for quick preview. Regenerate everything with `python3 build.py`.

## Subject

How the OASIS publication quality architecture's two layers dovetail:

- **Layer 1, validation (pub-check):** mechanical, tool-side. `pub_check.py`, 92
  checks across 34 check classes. The TC runs it in its own CI before submission,
  and TC Administration re-runs the identical code at intake. It only ever sees the
  package files. Output: the Validation Report — every one of the 92 conditions with
  the observed value the tool pulled set against the expected value it was compared
  to, never truncated (rendered landscape so the full values stay legible).
- **Layer 2, the publication audit:** human and adversarial, event-side. 15 to 16
  gates run against live ground truth the tool cannot see (byte identity, render
  class vs precedent, live roster, Naming Directives, index chain, zip integrity,
  four announcement channels, ticket record, an independent adversarial verifier,
  a literal visual eyeball). Output: the Publication Audit Report.
- **The dovetail:** audit gate 4b requires running pub-check and triaging every
  finding, so the whole 92-check validation layer plugs into the audit as one gate.
  Both reports are filed to the TC's ticket and the internal `_audit/` directory.

## Files

### `validation-audit-dovetail.svg` (1400 x 900, landscape) - flagship
Two swim lanes, TC side (Layer 1) and TC Administration side (Layer 2). A single
shared `pub-check` engine sits in the seam between them with dovetail tabs seating
into both lanes, showing the identical code running on both sides: the TC in CI on
the left, audit gate 4b on the right. The audit gates that need live ground truth
are laid out as a chip grid, the independent adversarial verifier is called out
separately, and both report artifacts flow down to the shared TCADMIN ticket and
`_audit/` repo. Intended use: the primary explainer figure for Stefan Hagen and TC
editors, and in TC Administration process documentation.

### `two-layer-stack.svg` (900 x 1100, portrait) - slide summary
A vertical stack that reads bottom to top: package in, Layer 1 validation, the gate
4b dovetail joint, Layer 2 audit, published and verified publication. Each layer
carries a "what the tool sees" (Layer 1) versus "what only a human or live check can
see" (Layer 2) annotation panel. Intended use: a single slide in a deck, or a
sidebar summary next to the flagship diagram.

## Rendering

```bash
python3 build.py                                        # writes both SVGs
rsvg-convert -z 2 validation-audit-dovetail.svg -o validation-audit-dovetail.png
rsvg-convert -z 2 two-layer-stack.svg -o two-layer-stack.png
```

Any of `rsvg-convert`, `qlmanage`, LibreOffice `soffice`, or `cairosvg` will render
these SVGs; `rsvg-convert` was used for the checked-in PNGs.
