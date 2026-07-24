#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Generate every SVG diagram in assets/ from one design system.

Eight diagrams, one set of tokens (the OASIS TC Handbook visual system:
Poppins, ink #0a2540, accent #2248e5, hairline borders, 2px radii):

  hero.svg                                 README masthead
  gate.svg                                 pub-check validation flow
  pipeline.svg                             the three pipeline stages
  chain.svg                                the end-to-end verification chain
  architecture/validation-audit-dovetail.svg   flagship two-lane architecture
  architecture/two-layer-stack.svg             portrait slide summary
  authority.svg                            policy provenance: one criterion, sourced
  architecture/nide-bridge.svg             how pub-check dovetails with nide

Self-contained SVG: shapes and <text> only, no scripts, no external refs.
Text uses the Poppins stack and falls back to Helvetica/Arial where Poppins
is not installed (layout is sized for Poppins, the widest of the three).

  python3 build.py            # writes all six SVGs
  python3 build.py --png      # also renders 2x PNGs via rsvg-convert
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ARCH = OUT / "architecture"

# ---- design tokens (OASIS TC Handbook system) -----------------------------
CLOUD   = "#edf3f9"   # page background
SURFACE = "#fafcfe"   # card surface
SURF2   = "#f2f6fb"   # surface-alt / panel interior
INK     = "#0a2540"   # headings, strong text
BODY    = "#313131"   # body text
MUTED   = "#6b7380"   # secondary text
BORDER  = "#d5dae0"   # hairline
BORDER2 = "#aeb7c4"   # strong hairline
ACCENT  = "#2248e5"   # accent blue: pub-check, TC side, primary
ACC_T   = "#e7ecfc"   # accent tint (fills behind accent-bordered elements)
NAVY3   = "#0a4a8f"   # TC Administration side, INFO severity
NAVY_T  = "#e8eef6"   # navy tint
GOOD    = "#15803d"   # pass / publishable
GOOD_T  = "#e9f3ec"   # green tint
RED     = "#b3261e"   # BLOCKER severity
RED_T   = "#f9ecea"   # red tint
RUST    = "#b94a0d"   # WARN severity / caution
RUST_T  = "#faf0e8"   # rust tint

FONT = "Poppins, 'Helvetica Neue', Arial, sans-serif"
MONO = "'IBM Plex Mono', Menlo, Consolas, monospace"

R = 2          # card corner radius
HAIR = 1       # hairline stroke
EMPH = 1.5     # emphasis stroke


# ---- primitives ------------------------------------------------------------
def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_open(w: int, h: int) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">')


def canvas(w: int, h: int) -> str:
    return (f'<rect width="{w}" height="{h}" fill="{CLOUD}"/>'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" fill="none" '
            f'stroke="{BORDER}" stroke-width="1"/>')


def rect(x, y, w, h, fill=SURFACE, stroke=BORDER, sw=HAIR, r=R, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = f' stroke="{stroke}" stroke-width="{sw}"{d}' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" fill="{fill}"{s}/>'


def text(x, y, s, size=12, fill=BODY, w=400, anchor="start", ls=None, font=FONT):
    lsa = f' letter-spacing="{ls}"' if ls else ""
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
            f'font-weight="{w}" fill="{fill}" text-anchor="{anchor}"{lsa}>{esc(s)}</text>')


def kicker(x, y, s, fill=NAVY3):
    return text(x, y, s.upper(), 10.5, fill, 500, ls=2.2)


def label(x, y, s, fill=INK, size=12, anchor="start"):
    return text(x, y, s.upper(), size, fill, 500, anchor=anchor, ls=1.1)


def rule(x1, y1, x2, y2, stroke=BORDER, sw=HAIR, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def marker_defs() -> str:
    def m(mid, color):
        return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="8.5" refY="5" '
                f'markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
                f'<path d="M0,1 L9,5 L0,9 z" fill="{color}"/></marker>')
    return ("<defs>" + m("aInk", INK) + m("aAcc", ACCENT) + m("aNavy", NAVY3) +
            m("aMut", BORDER2) + m("aGood", GOOD) + m("aRed", RED) + "</defs>")


def arrow(x1, y1, x2, y2, color=INK, sw=1.4, mk="aInk"):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" marker-end="url(#{mk})"/>')


def path_arrow(d, color=INK, sw=1.4, mk="aInk"):
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'marker-end="url(#{mk})"/>')


def pill(cx, cy, s, fill, size=9.5, padx=9):
    w = est_w(s, size, 700) + 2 * padx
    h = size + 8
    return (rect(cx - w / 2, cy - h / 2, w, h, fill, None, 0, r=h / 2) +
            text(cx, cy + size * 0.36, s, size, "#ffffff", 700, anchor="middle", ls=0.5))


def sev_badges(cx, cy, gap=8):
    """BLOCKER / WARN / INFO severity pills centered on cx."""
    items = [("BLOCKER", RED), ("WARN", RUST), ("INFO", NAVY3)]
    widths = [est_w(t, 9.5, 700) + 18 for t, _ in items]
    total = sum(widths) + gap * 2
    x = cx - total / 2
    out = []
    for (t, c), w in zip(items, widths):
        out.append(pill(x + w / 2, cy, t, c))
        x += w + gap
    return "".join(out)


def doc_glyph(x, y, w, h, fold=16, stroke=INK, sw=EMPH):
    """Document silhouette with a folded corner."""
    return (f'<path d="M{x},{y} H{x+w-fold} L{x+w},{y+fold} V{y+h} H{x} Z" '
            f'fill="{SURFACE}" stroke="{stroke}" stroke-width="{sw}"/>'
            f'<path d="M{x+w-fold},{y} V{y+fold} H{x+w}" fill="none" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')


def numdot(cx, cy, n, r=11, color=ACCENT):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="1.5"/>' +
            text(cx, cy + 4, str(n), 12, color, 700, anchor="middle"))


def dot(cx, cy, color=NAVY3, r=2.6):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'


def est_w(s: str, size: float, weight: int = 400) -> float:
    """Rough Poppins width estimate; sized for the widest font in the stack."""
    k = 0.60 if weight < 500 else (0.63 if weight < 700 else 0.66)
    caps = sum(1 for c in s if c.isupper()) / max(len(s), 1)
    return len(s) * size * (k + 0.10 * caps)


def write(path: Path, parts: list[str]) -> None:
    path.write_text("\n".join(parts) + "\n")
    print(f"wrote {path.relative_to(OUT.parent)}")


def oasis_logo(x, y, w):
    """The canonical OASIS logo (assets/OASISLogo-v3.0.png, 306x63),
    base64-embedded so the SVG stays self-contained."""
    import base64
    b64 = base64.b64encode((OUT / "OASISLogo-v3.0.png").read_bytes()).decode()
    h = w * 63 / 306
    return (f'<image x="{x}" y="{y}" width="{w}" height="{h}" '
            f'href="data:image/png;base64,{b64}"/>')


# ===========================================================================
# hero.svg (1200 x 270)  README masthead
# ===========================================================================
def build_hero():
    W, H = 1200, 270
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]

    # left: logo lockup + editorial title block
    e.append(oasis_logo(56, 42, 160))
    e.append(text(56, 128, "Publication Assurance", 30, INK, 700))
    e.append(text(56, 158, "The pipeline, the acceptance gate, and the publication audit", 13.5, BODY))
    e.append(text(56, 178, "behind docs.oasis-open.org.", 13.5, BODY))
    e.append(text(56, 218, "Michael Coletta  ·  Technical Advisor, OASIS Open  ·  TC Administration", 11, MUTED))

    # right: any source converging into the fixed output contract, then the gate
    x0 = 742
    scw, sch = 82, 26
    ys = [40, 72, 104, 136]
    for y, t in zip(ys, [".md", ".docx", ".odt", "*.*"]):
        e.append(rect(x0, y, scw, sch, SURFACE, BORDER2, HAIR))
        e.append(text(x0 + scw / 2, y + 17.5, t, 12.5, INK, 500, anchor="middle", font=MONO))
        e.append(rule(x0 + scw + 4, y + sch / 2, 878, y + sch / 2, BORDER2, 1.2))
    e.append(rule(878, ys[0] + sch / 2, 878, ys[-1] + sch / 2, BORDER2, 1.2))
    e.append(arrow(878, 101, 928, 101, ACCENT, 1.5, "aAcc"))
    e.append(text(x0, 184, "any source the TC authors in", 10, MUTED))

    ocw, och = 150, 44
    e.append(rect(936, 79, ocw, och, SURFACE, ACCENT, EMPH))
    e.append(text(936 + ocw / 2, 106, ".html + .pdf", 14, ACCENT, 500, anchor="middle", font=MONO))
    e.append(text(936 + ocw / 2, 141, "the fixed output contract", 10, MUTED, anchor="middle"))

    gx, gy, gw, gh = x0, 190, 372, 44
    e.append(rect(gx, gy, gw, gh, GOOD_T, GOOD, EMPH))
    e.append(text(gx + gw / 2, gy + 27, "oasis-pub-check · 164 checks · exit 0 = publish",
                  13, GOOD, 500, anchor="middle", font=MONO))

    e.append("</svg>")
    write(OUT / "hero.svg", e)


# ===========================================================================
# gate.svg (1200 x 600)  pub-check validation flow
# ===========================================================================
def build_gate():
    W, H = 1200, 600
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]
    e.append(oasis_logo(W - 196, 42, 140))

    e.append(kicker(56, 52, "Layer 1 · Validation"))
    e.append(text(56, 86, "oasis-pub-check: the acceptance criteria", 26, INK, 700))
    e.append(text(56, 112, "One stdlib Python file. Every check is sourced from written OASIS policy "
                           "(the TC Process, Naming Directives v1.7, the TC Handbook) or a real correction round.", 12.5, MUTED))

    # left: work product
    wx, wy, ww, wh = 56, 210, 200, 190
    e.append(rect(wx, wy, ww, wh, SURFACE, BORDER2, HAIR))
    e.append(label(wx + 18, wy + 32, "Work product", INK, 12))
    e.append(rule(wx + 18, wy + 44, wx + ww - 18, wy + 44))
    for i, t in enumerate(["spec-vN.N-csdNN", ".md | .docx | .odt | *.*", "+ .html + .pdf",
                           "schema/*.json", "manifest.json"]):
        e.append(text(wx + 18, wy + 66 + i * 24, t, 11.5, BODY, 400, font=MONO))
    e.append(arrow(wx + ww + 8, wy + wh / 2, wx + ww + 42, wy + wh / 2, INK, 1.4))

    # center: grouped checks panel
    px, py, pw, ph = 306, 152, 564, 356
    e.append(rect(px, py, pw, ph, SURFACE, BORDER2, HAIR, r=3))
    e.append(text(px + 24, py + 36, "164 checks in 55 classes", 16, INK, 700))
    e.append(text(px + pw - 24, py + 36, "grouped by what they protect", 11, MUTED, anchor="end"))
    e.append(rule(px + 24, py + 50, px + pw - 24, py + 50))

    groups = [
        ("Naming, versions & URIs", 53, "stage tokens, versions, filenames, URIs, XML namespaces"),
        ("Front matter & links", 34, "This/Latest URLs, titles, authors, anchors, dead lists"),
        ("Content, refs & residue", 14, "TODO/tbd, normative/informative refs, non-normative labels"),
        ("Template & conformance", 15, "template sections, Conformance structure, RFC 2119, logo"),
        ("Rendering & sync", 25, "PDF sync, fonts, images, Word fidelity"),
        ("Package & provenance", 23, "junk, symlinks, schema $id, manifest, ODT integrity"),
    ]
    gw, gh, ggx, ggy = 250, 78, 16, 14
    for i, (name, n, det) in enumerate(groups):
        col, row = i % 2, i // 2
        gx = px + 24 + col * (gw + ggx)
        gy = py + 66 + row * (gh + ggy)
        e.append(rect(gx, gy, gw, gh, SURF2, BORDER, HAIR))
        e.append(text(gx + 14, gy + 26, name, 12.5, INK, 500))
        e.append(text(gx + gw - 14, gy + 26, str(n), 12.5, ACCENT, 700, anchor="end", font=MONO))
        # wrap detail at ~40 chars
        if len(det) > 40:
            cut = det.rfind(",", 0, 40)
            e.append(text(gx + 14, gy + 46, det[:cut + 1], 10.5, MUTED))
            e.append(text(gx + 14, gy + 62, det[cut + 2:], 10.5, MUTED))
        else:
            e.append(text(gx + 14, gy + 46, det, 10.5, MUTED))

    e.append(text(px + 24, py + ph + 28,
                  "Code fences and pre/code content are excluded from prose checks.", 11, MUTED))
    e.append(text(px + 24, py + ph + 46,
                  "Track-aware: the source travels as .md, .docx, or .odt; the output "
                  "contract (HTML + PDF) is fixed.", 11, MUTED))

    # right: exits
    ex, ew, eh = 926, 218, 108
    e.append(arrow(px + pw + 8, 262, ex - 8, 262, GOOD, 1.5, "aGood"))
    e.append(arrow(px + pw + 8, 414, ex - 8, 414, RED, 1.5, "aRed"))
    e.append(rect(ex, 208, ew, eh, GOOD_T, GOOD, EMPH))
    e.append(text(ex + 18, 240, "exit 0 · publishable", 14.5, GOOD, 700, font=MONO))
    e.append(text(ex + 18, 266, "no resubmission cycle:", 11.5, BODY))
    e.append(text(ex + 18, 284, "intake verifies and publishes", 11.5, BODY))
    e.append(rect(ex, 360, ew, eh, RED_T, RED, EMPH))
    e.append(text(ex + 18, 392, "exit 1 · blockers", 14.5, RED, 700, font=MONO))
    e.append(text(ex + 18, 418, "resolve every blocker", 11.5, BODY))
    e.append(text(ex + 18, 436, "before the TC votes", 11.5, BODY))

    e.append("</svg>")
    write(OUT / "gate.svg", e)


# ===========================================================================
# pipeline.svg (1200 x 330)  the three pipeline stages
# ===========================================================================
def build_pipeline():
    W, H = 1200, 330
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]
    e.append(oasis_logo(W - 176, 42, 120))

    e.append(kicker(56, 52, "The publication pipeline"))
    e.append(text(56, 86, "Three stages, six commands", 26, INK, 700))
    e.append(text(56, 112, "The workflow YAML around these commands is CI plumbing only. "
                           "Full command reference: TRANSFORMS.md.", 12.5, MUTED))

    stages = [
        ("Markdown to HTML", ["prettier --write spec.md",
                              "pandoc -f markdown+autolink...",
                              "9 OASIS HTML fix-ups (python)"]),
        ("HTML to PDF", ["fix_html_for_pdf.py",
                         "wkhtmltopdf + A4 + footers"]),
        ("Package", ["zip -r spec-stage.zip ."]),
    ]
    cw, chh, gap = 330, 158, 40
    x0, y0 = 56, 140
    for i, (name, cmds) in enumerate(stages):
        x = x0 + i * (cw + gap)
        e.append(rect(x, y0, cw, chh, SURFACE, BORDER2, HAIR, r=3))
        e.append(numdot(x + 26, y0 + 28, i + 1))
        e.append(text(x + 46, y0 + 33, name, 14, INK, 500))
        e.append(rule(x + 18, y0 + 48, x + cw - 18, y0 + 48))
        for j, c in enumerate(cmds):
            cy = y0 + 62 + j * 32
            e.append(rect(x + 18, cy, cw - 36, 24, SURF2, BORDER, HAIR))
            e.append(text(x + 28, cy + 16.5, c, 11, BODY, 400, font=MONO))
        if i < 2:
            e.append(arrow(x + cw + 8, y0 + chh / 2, x + cw + gap - 8, y0 + chh / 2,
                           ACCENT, 1.5, "aAcc"))
        if i == 1:
            e.append(text(x + 18, y0 + chh - 16,
                          "production renders via headless Chrome + CSS Paged Media",
                          10, MUTED))
        if i == 2:
            e.append(text(x + 18, y0 + 110,
                          "then every shipped file is stamped with the", 10, MUTED))
            e.append(text(x + 18, y0 + 126,
                          "publication date (release management, not a transform)", 10, MUTED))
    e.append("</svg>")
    write(OUT / "pipeline.svg", e)


# ===========================================================================
# chain.svg (1200 x 300)  end-to-end verification chain
# ===========================================================================
def build_chain():
    W, H = 1200, 300
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]
    e.append(oasis_logo(W - 176, 42, 120))

    e.append(kicker(56, 52, "Provenance"))
    e.append(text(56, 86, "The verification chain", 26, INK, 700))

    nodes = [
        ("TC build", ["make / CI / editor tools", "renders source · html · pdf"], SURFACE, BORDER2, INK),
        ("manifest.json", ["sha256 + roles", "source commit · tools"], SURFACE, BORDER2, INK),
        ("oasis-pub-check", ["164 checks, before the vote", "TC side · exit 0"], ACC_T, ACCENT, ACCENT),
        ("OASIS intake", ["independent re-run", "gate + audit record"], SURFACE, BORDER2, INK),
        ("docs.oasis-open.org", ["published"], INK, INK, "#ffffff"),
    ]
    cw, chh, gap = 196, 92, 28
    x0, yc = 56, 172
    for i, (name, lines, fill, stroke, tcol) in enumerate(nodes):
        x = x0 + i * (cw + gap)
        sw = EMPH if stroke in (ACCENT, INK) else HAIR
        e.append(rect(x, yc - chh / 2, cw, chh, fill, stroke, sw))
        mono = name in ("manifest.json", "oasis-pub-check")
        e.append(text(x + cw / 2, yc - chh / 2 + 30, name, 13.5, tcol, 700,
                      anchor="middle", font=MONO if mono else FONT))
        sub = "#c8d4e2" if fill == INK else MUTED
        for j, ln in enumerate(lines):
            e.append(text(x + cw / 2, yc - chh / 2 + 51 + j * 17, ln, 10.5, sub, 400,
                          anchor="middle"))
        if i < 4:
            e.append(arrow(x + cw + 6, yc, x + cw + gap - 6, yc, BORDER2, 1.4, "aMut"))

    e.append(text(56, 258, "Identical criteria run on both sides; every artifact is "
                           "verified by sha256 at each step.", 11.5, MUTED))
    e.append("</svg>")
    write(OUT / "chain.svg", e)


# ===========================================================================
# architecture/validation-audit-dovetail.svg (1400 x 900)  flagship
# ===========================================================================
def build_dovetail():
    W, H = 1400, 900
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]
    e.append(oasis_logo(W - 206, 38, 150))

    # title block
    e.append(kicker(56, 46, "Publication quality architecture"))
    e.append(text(56, 78, "How the two layers dovetail", 26, INK, 700))
    e.append(text(56, 102, "One validation engine runs on both sides; the publication audit "
                           "wraps it with the gates only a human or a live check can run.",
                  12.5, MUTED))

    # ---- lane panels ----
    LY, LH = 128, 640
    LX1, LX2, LW = 56, 824, 520
    HH = 46
    for lx, hcol, l1, l2 in (
        (LX1, ACCENT, "LAYER 1 · VALIDATION · TC SIDE",
         "The TC and its editors: “Is the document ready?”"),
        (LX2, NAVY3, "LAYER 2 · PUBLICATION AUDIT · TC ADMINISTRATION",
         "The publication event: “Did we publish it right?”"),
    ):
        e.append(rect(lx, LY, LW, LH, SURFACE, BORDER2, HAIR, r=3))
        e.append(f'<path d="M{lx+3},{LY} H{lx+LW-3} A3,3 0 0 1 {lx+LW},{LY+3} '
                 f'V{LY+HH} H{lx} V{LY+3} A3,3 0 0 1 {lx+3},{LY} Z" fill="{hcol}"/>')
        cx = lx + LW / 2
        e.append(text(cx, LY + 20, l1, 13.5, "#ffffff", 700, anchor="middle", ls=0.8))
        e.append(text(cx, LY + 37, l2, 11, "#dbe4f4", 400, anchor="middle"))

    lcx = LX1 + LW / 2   # 316
    rcx = LX2 + LW / 2   # 1084

    # ---- LEFT lane content (even vertical rhythm) ----
    bx, bw = LX1 + 20, LW - 40
    e.append(rect(bx, 200, bw, 104, SURFACE, BORDER2, HAIR))
    e.append(numdot(bx + 26, 228, 1))
    e.append(text(bx + 46, 233, "PACKAGE ASSEMBLED", 13, INK, 500, ls=1.0))
    e.append(text(bx + 46, 262, "filenames · case · front matter · anchors · fonts", 11, MUTED))
    e.append(text(bx + 46, 282, "placeholders · schema $id · stage naming · junk files", 11, MUTED))
    e.append(arrow(lcx, 308, lcx, 344, INK, 1.4))

    e.append(rect(bx, 348, bw, 118, SURFACE, ACCENT, EMPH))
    e.append(numdot(bx + 26, 376, 2))
    e.append(text(bx + 46, 381, "RUN oasis-pub-check IN THE TC'S OWN CI", 13, INK, 500, ls=0.6))
    e.append(text(bx + 46, 410, "before submission, in the TC's own build:", 11.5, BODY))
    e.append(text(bx + 46, 429, "the TC runs the exact gate TC Administration runs", 11.5, BODY))
    e.append(text(bx + 46, 450, "the TC owns “the document is ready”", 11.5, ACCENT, 500))
    e.append(arrow(lcx, 470, lcx, 502, INK, 1.4))

    e.append(doc_glyph(bx + 16, 506, bw - 32, 96, 16, ACCENT, EMPH))
    e.append(text(lcx, 538, "VALIDATION REPORT", 13, ACCENT, 700, anchor="middle", ls=1.0))
    e.append(text(lcx, 560, "all 164 conditions: observed vs expected, in full", 11, BODY, anchor="middle"))
    e.append(text(lcx, 580, "zero blockers = publication-ready package", 11, INK, 500, anchor="middle"))
    e.append(arrow(lcx, 606, lcx, 642, INK, 1.4))

    e.append(rect(lcx - 180, 646, 360, 38, ACCENT, None, 0, r=19))
    e.append(text(lcx, 670, "SUBMIT PACKAGE TO TC ADMINISTRATION", 12, "#ffffff", 700,
                  anchor="middle", ls=0.5))
    e.append(text(lcx + 14, 716, "nothing bounces back:", 10.5, MUTED))
    e.append(text(lcx + 14, 732, "the vote is on a clean package", 10.5, MUTED))

    # ---- RIGHT lane content ----
    rbx, rbw = LX2 + 20, LW - 40
    e.append(rect(rbx, 196, rbw, 54, SURFACE, BORDER2, HAIR))
    e.append(text(rcx, 218, "INTAKE", 13, INK, 500, anchor="middle", ls=1.2))
    e.append(text(rcx, 237, "package + Validation Report received by TC Administration", 11, MUTED, anchor="middle"))
    e.append(arrow(rcx, 250, rcx, 316, INK, 1.4))

    e.append(rect(rbx, 320, rbw, 104, ACC_T, ACCENT, 2))
    e.append(text(rcx, 346, "CHECKLIST STEP 4b · THE DOVETAIL JOINT", 13, ACCENT, 700,
                  anchor="middle", ls=0.6))
    e.append(text(rcx, 369, "re-run oasis-pub-check, triage every finding:", 11.5, BODY, anchor="middle"))
    e.append(text(rcx, 387, "the whole 164-check validation layer plugs in here", 11.5, BODY, anchor="middle"))
    e.append(text(rcx, 406, "trust, but verify: identical code, our side", 11.5, ACCENT, 500, anchor="middle"))

    e.append(label(rbx, 452, "Gates only a human or live check can run", NAVY3, 11.5))
    e.append(text(rbx, 469, "live ground truth the tool never sees", 10.5, MUTED))

    chips = [
        ["GitHub vs live", "byte identity"],
        ["Render class", "vs TC precedent"],
        ["Front matter", "vs live roster"],
        ["Current Naming", "Directives"],
        ["Live directory", "index chain"],
        ["Zip integrity"],
        ["Announcement", "channels, all four"],
        ["TCADMIN", "ticket record"],
        ["Visual eyeball", "of the live page"],
    ]
    ccw, cch, cgx, cgy = 152, 46, 12, 10
    gx0, gy0 = rbx, 482
    for i, lines in enumerate(chips):
        col, row = i % 3, i // 3
        cx0 = gx0 + col * (ccw + cgx)
        cy0 = gy0 + row * (cch + cgy)
        e.append(rect(cx0, cy0, ccw, cch, SURF2, BORDER, HAIR))
        e.append(dot(cx0 + 15, cy0 + cch / 2))
        if len(lines) == 2:
            e.append(text(cx0 + 27, cy0 + cch / 2 - 3, lines[0], 10.5, INK, 500))
            e.append(text(cx0 + 27, cy0 + cch / 2 + 13, lines[1], 10.5, INK, 500))
        else:
            e.append(text(cx0 + 27, cy0 + cch / 2 + 4, lines[0], 10.5, INK, 500))

    wy = gy0 + 3 * (cch + cgy)   # 650
    e.append(rect(gx0, wy, ccw * 3 + cgx * 2, 38, RUST_T, RUST, HAIR))
    e.append(dot(gx0 + 15, wy + 19, RUST))
    e.append(text(gx0 + 27, wy + 24, "Independent adversarial verifier · refute mandate",
                  11, RUST, 500))

    dy = wy + 50   # 700
    e.append(doc_glyph(rbx + 16, dy, rbw - 32, 60, 16, NAVY3, EMPH))
    e.append(text(rcx, dy + 25, "PUBLICATION AUDIT REPORT", 13, NAVY3, 700, anchor="middle", ls=0.8))
    e.append(text(rcx, dy + 45, "15 mandatory gates, evidence recorded; verdict computed, not asserted",
                  10.5, MUTED, anchor="middle"))

    # submitted package handoff, drawn FIRST so the engine, tabs, and banner
    # pill sit over it (the riser crosses the left tab's x-range; painting
    # order keeps the joint visually clean instead of struck through)
    e.append(path_arrow(f"M{lcx+182},665 H{LX1+LW+22} V274 H{rcx-84} V256",
                        BORDER2, 1.4, "aMut"))
    e.append(text(700, 264, "submitted package", 10.5, MUTED, anchor="middle"))

    # ---- CENTER shared engine ----
    ex, ey, ew, eh = 606, 320, 188, 190
    ecx, emid = ex + ew / 2, ey + eh / 2
    # dovetail keys seating 4px into each lane border (drawn over the lanes)
    TAB = "#c9d6f8"
    tabL = f'{ex},{ey+52} {ex-34},{ey+42} {ex-34},{ey+eh-42} {ex},{ey+eh-52}'
    tabR = f'{ex+ew},{ey+52} {ex+ew+34},{ey+42} {ex+ew+34},{ey+eh-42} {ex+ew},{ey+eh-52}'
    for t in (tabL, tabR):
        e.append(f'<polygon points="{t}" fill="{TAB}" stroke="{ACCENT}" stroke-width="1.3"/>')
    e.append(arrow(ex - 28, emid, ex - 7, emid, ACCENT, 1.5, "aAcc"))
    e.append(arrow(ex + ew + 7, emid, ex + ew + 28, emid, ACCENT, 1.5, "aAcc"))

    e.append(rect(ex, ey, ew, eh, SURFACE, ACCENT, 1.6, r=3))
    e.append(f'<path d="M{ex+3},{ey} H{ex+ew-3} A3,3 0 0 1 {ex+ew},{ey+3} V{ey+30} '
             f'H{ex} V{ey+3} A3,3 0 0 1 {ex+3},{ey} Z" fill="{ACCENT}"/>')
    e.append(text(ecx, ey + 20, "oasis-pub-check", 13.5, "#ffffff", 700, anchor="middle", font=MONO))
    e.append(text(ecx, ey + 52, "oasis_pub_check.py", 11.5, ACCENT, 500, anchor="middle", font=MONO))
    e.append(text(ecx, ey + 74, "164 individual checks", 11.5, BODY, anchor="middle"))
    e.append(text(ecx, ey + 92, "35 check classes", 11.5, BODY, anchor="middle"))
    e.append(rule(ex + 16, ey + 104, ex + ew - 16, ey + 104, BORDER, dash="3 3"))
    e.append(sev_badges(ecx, ey + 122))
    e.append(text(ecx, ey + 152, "sees only the package files,", 10, MUTED, anchor="middle"))
    e.append(text(ecx, ey + 167, "never the live site", 10, MUTED, anchor="middle"))

    e.append(pill(ecx, ey - 22, "IDENTICAL CODE, BOTH SIDES", INK, 10))
    e.append(text(ex - 4, ey + eh + 22, "run in TC CI", 10.5, ACCENT, 500))
    e.append(text(ex + ew + 4, ey + eh + 22, "re-run at intake", 10.5, ACCENT, 500, anchor="end"))

    # ---- bottom band: the shared record ----
    tby, tbw, tbh = 800, 400, 84
    tbx = W / 2 - tbw / 2
    e.append(rect(tbx, tby, tbw, tbh, INK, None, 0, r=3))
    e.append(text(W / 2, tby + 30, "TCADMIN TICKET + _audit/ REPO", 13.5, "#ffffff", 700,
                  anchor="middle", ls=0.8))
    e.append(text(W / 2, tby + 52, "both standard reports filed here:", 10.5, "#c8d4e2", anchor="middle"))
    e.append(text(W / 2, tby + 69, "the shared record of the publication", 10.5, "#c8d4e2", anchor="middle"))
    e.append(path_arrow(f"M{lcx},684 V{tby+42} H{tbx-6}", INK, 1.4))
    e.append(path_arrow(f"M{rcx},{dy+60} V{tby+42} H{tbx+tbw+6}", INK, 1.4))
    e.append(text(lcx + 14, tby + 28, "Validation Report", 10.5, MUTED))
    e.append(text(rcx - 14, tby + 28, "Audit Report", 10.5, MUTED, anchor="end"))

    e.append("</svg>")
    write(ARCH / "validation-audit-dovetail.svg", e)


# ===========================================================================
# architecture/two-layer-stack.svg (900 x 1100)  portrait slide summary
# ===========================================================================
def build_stack():
    W, H = 900, 1100
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]
    e.append(oasis_logo(W - 196, 40, 140))

    e.append(kicker(56, 48, "Publication quality architecture"))
    e.append(text(56, 80, "The OASIS publication quality stack", 24, INK, 700))
    e.append(text(56, 104, "Package in at the bottom, verified publication at the top; "
                           "two layers joined at checklist step 4b.", 12, MUTED))

    # readiness axis
    e.append(arrow(34, 1020, 34, 300, BORDER2, 3, "aMut"))
    e.append(f'<text transform="rotate(-90 22 660)" x="22" y="660" font-family="{FONT}" '
             f'font-size="10.5" font-weight="500" fill="{MUTED}" text-anchor="middle" '
             f'letter-spacing="2">PUBLICATION READINESS</text>')

    # -------- PACKAGE IN (bottom) --------
    e.append(rect(260, 990, 380, 64, SURFACE, BORDER2, HAIR))
    e.append(text(450, 1017, "PACKAGE IN", 14, INK, 500, anchor="middle", ls=1.4))
    e.append(text(450, 1038, "the assembled TC submission package", 11.5, MUTED, anchor="middle"))
    e.append(arrow(450, 988, 450, 966, INK, 1.4))

    # -------- LAYER 1 : VALIDATION --------
    L1Y, L1H = 742, 220
    e.append(rect(70, L1Y, 760, L1H, SURFACE, BORDER2, HAIR, r=3))
    e.append(f'<path d="M73,{L1Y} H827 A3,3 0 0 1 830,{L1Y+3} V{L1Y+38} H70 V{L1Y+3} '
             f'A3,3 0 0 1 73,{L1Y} Z" fill="{ACCENT}"/>')
    e.append(text(450, L1Y + 25, "LAYER 1 · VALIDATION · oasis-pub-check (mechanical, tool-side)",
                  13.5, "#ffffff", 700, anchor="middle", ls=0.6))
    e.append(text(100, L1Y + 68, "oasis_pub_check.py: 164 checks across 55 classes", 13, INK, 700))
    e.append(text(100, L1Y + 92, "Runs in the TC's own CI before submission.", 11.5, BODY))
    e.append(text(100, L1Y + 111, "Re-run identically by TC Administration at intake (step 4b).", 11.5, BODY))
    e.append(text(100, L1Y + 136, "Every finding gets a severity:", 11.5, BODY))
    e.append(sev_badges(190, L1Y + 158))
    e.append(text(100, L1Y + 194, "Output: a Validation Report, observed vs expected for all 164.",
                  11.5, ACCENT, 500))
    # annotation panel
    e.append(rect(520, L1Y + 54, 286, 148, SURFACE, ACCENT, 1.2, dash="5 4"))
    e.append(label(534, L1Y + 78, "What the tool sees", ACCENT, 11))
    for i, s in enumerate(["filenames · case · front matter", "anchors · fonts · placeholders",
                           "schema $id · stage naming", "image policy · junk files"]):
        e.append(text(534, L1Y + 100 + i * 19, s, 11, BODY))
    e.append(text(534, L1Y + 138 + 3 * 19, "only the package, never the live site", 10, MUTED))

    # -------- LAYER 2 : AUDIT --------
    L2Y, L2H = 306, 376
    e.append(rect(70, L2Y, 760, L2H, SURFACE, BORDER2, HAIR, r=3))
    e.append(f'<path d="M73,{L2Y} H827 A3,3 0 0 1 830,{L2Y+3} V{L2Y+38} H70 V{L2Y+3} '
             f'A3,3 0 0 1 73,{L2Y} Z" fill="{NAVY3}"/>')
    e.append(text(450, L2Y + 25, "LAYER 2 · PUBLICATION AUDIT · human + adversarial (event-side)",
                  13.5, "#ffffff", 700, anchor="middle", ls=0.4))
    gates = [
        ("Step 4b: run oasis-pub-check + triage findings (the dovetail)", ACCENT, 500, ACCENT),
        ("GitHub vs live byte identity", NAVY3, 400, BODY),
        ("Render class vs the TC's own precedent", NAVY3, 400, BODY),
        ("Front matter vs the live roster", NAVY3, 400, BODY),
        ("Current Naming Directives", NAVY3, 400, BODY),
        ("Live directory index chain", NAVY3, 400, BODY),
        ("Zip integrity", NAVY3, 400, BODY),
        ("Four announcement channels at destination", NAVY3, 400, BODY),
        ("TCADMIN ticket record", NAVY3, 400, BODY),
        ("Independent adversarial verifier (refute mandate)", NAVY3, 400, BODY),
        ("Visual eyeball of the live page", NAVY3, 400, BODY),
    ]
    for i, (s, col, wgt, tcol) in enumerate(gates):
        y = L2Y + 66 + i * 26
        e.append(dot(104, y - 4, col))
        e.append(text(118, y, s, 11.5, tcol, wgt))
    # annotation panel
    e.append(rect(520, L2Y + 54, 286, 236, SURFACE, NAVY3, 1.2, dash="5 4"))
    e.append(label(534, L2Y + 78, "What only a human or", NAVY3, 11))
    e.append(label(534, L2Y + 95, "live check can see", NAVY3, 11))
    e.append(text(534, L2Y + 120, "Live ground truth the tool cannot reach:", 10.5, BODY))
    for i, s in enumerate(["the running site", "the roster as it stands today",
                           "the announcement destinations", "the rendered page",
                           "an adversary set to refute it"]):
        e.append(dot(541, L2Y + 142 + i * 22, NAVY3))
        e.append(text(554, L2Y + 146 + i * 22, s, 11, BODY))
    e.append(text(100, L2Y + L2H - 14,
                  "The audit record carries 15 mandatory gates (sub-gates grouped above); "
                  "every gate needs evidence.", 10.5, MUTED))

    # -------- dovetail joint (drawn over both layer panels) --------
    tab = f'400,{L1Y+4} 500,{L1Y+4} 514,{L2Y+L2H-4} 386,{L2Y+L2H-4}'
    e.append(f'<polygon points="{tab}" fill="#c9d6f8" stroke="{ACCENT}" stroke-width="1.3"/>')
    e.append(arrow(450, L1Y - 2, 450, 726, ACCENT, 1.5, "aAcc"))
    e.append(pill(450, 712, "STEP 4b · THE DOVETAIL", ACCENT, 10))

    # -------- PUBLISHED (top) --------
    e.append(rect(140, 140, 620, 132, INK, None, 0, r=3))
    e.append(f'<circle cx="212" cy="206" r="30" fill="none" stroke="{GOOD}" stroke-width="2.5"/>')
    e.append(f'<path d="M198,206 l10,11 l19,-22" fill="none" stroke="{GOOD}" '
             f'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
    e.append(text(478, 186, "PUBLISHED + VERIFIED PUBLICATION", 16, "#ffffff", 700,
                  anchor="middle", ls=0.8))
    e.append(text(478, 212, "live on docs.oasis-open.org", 12, "#c8d4e2", anchor="middle"))
    e.append(text(478, 232, "all four channels announced", 11, "#9fb2c8", anchor="middle"))
    e.append(text(478, 250, "both reports filed to the ticket and _audit/", 11, "#9fb2c8", anchor="middle"))
    e.append(arrow(450, 304, 450, 278, INK, 1.4))

    e.append("</svg>")
    write(ARCH / "two-layer-stack.svg", e)


# ===========================================================================
# authority.svg (1200 x 600)  policy provenance: one criterion, sourced end to end
# ===========================================================================
def build_authority():
    W, H = 1200, 600
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]
    e.append(oasis_logo(W - 196, 42, 140))
    e.append(kicker(56, 52, "Provenance · how the criteria are sourced"))
    e.append(text(56, 86, "Every check traces to a written rule", 26, INK, 700))
    e.append(text(56, 112, "Each acceptance criterion cites a verbatim clause from the OASIS "
                           "governing corpus, snapshotted and hashed. One worked example:", 12.5, MUTED))

    midy = 300

    # 1 · governing corpus
    cx, cy, cw, ch = 48, 190, 210, 234
    e.append(rect(cx, cy, cw, ch, SURFACE, BORDER2, HAIR))
    e.append(label(cx + 16, cy + 30, "Governing corpus", INK, 12))
    e.append(rule(cx + 16, cy + 42, cx + cw - 16, cy + 42))
    for i, d in enumerate(["OASIS TC Process", "Committee Operations",
                           "Naming Directives v1.7", "TC Handbook"]):
        gy = cy + 64 + i * 34
        e.append(doc_glyph(cx + 18, gy - 14, 14, 18))
        e.append(text(cx + 42, gy, d, 11.5, BODY, 500))
    e.append(text(cx + 16, cy + ch - 16, "25 pages · snapshotted + hashed", 10, MUTED))
    e.append(arrow(cx + cw + 6, midy, cx + cw + 40, midy, INK, 1.4))

    # 2 · verbatim clause
    qx, qy, qw, qh = cx + cw + 40, 172, 318, 252
    e.append(rect(qx, qy, qw, qh, SURFACE, BORDER2, HAIR))
    e.append(label(qx + 18, qy + 30, "Verbatim clause", INK, 12))
    e.append(rule(qx + 18, qy + 42, qx + qw - 18, qy + 42))
    e.append(text(qx + 18, qy + 62, "Naming Directives v1.7 · §6.6", 9.5, ACCENT, 600, font=MONO))
    for i, ln in enumerate([
            "“The OASIS member-only (private,",
            "password-protected) URI references …",
            "must not be cited in … any TC",
            "documents that are or may become",
            "public.”"]):
        e.append(text(qx + 18, qy + 88 + i * 25, ln, 12, INK, 400))
    e.append(text(qx + 18, qy + qh - 16, "the exact words, quoted, not paraphrased", 10, MUTED))
    e.append(arrow(qx + qw + 6, midy, qx + qw + 40, midy, INK, 1.4))
    e.append(text(qx + qw + 23, midy - 10, "derives", 9.5, MUTED, anchor="middle"))

    # 3 · acceptance criterion
    rx, ry, rw, rh = qx + qw + 40, 206, 224, 188
    e.append(rect(rx, ry, rw, rh, ACC_T, ACCENT, HAIR))
    e.append(label(rx + 16, ry + 30, "Acceptance criterion", INK, 12))
    e.append(text(rx + 16, ry + 52, "AC-PACKAGING-18", 11, ACCENT, 700, font=MONO))
    e.append(rule(rx + 16, ry + 62, rx + rw - 16, ry + 62, ACCENT, HAIR))
    for i, ln in enumerate(["No OASIS member-only", "(Kavi) URI may be cited",
                            "in a work product."]):
        e.append(text(rx + 16, ry + 86 + i * 20, ln, 12, INK, 500))
    e.append(pill(rx + 48, ry + rh - 24, "BLOCKER", RED, 9.5))
    e.append(arrow(rx + rw + 6, midy, rx + rw + 40, midy, INK, 1.4))

    # 4 · both gates
    fx = rx + rw + 40
    e.append(rect(fx, 196, 210, 96, SURF2, BORDER, HAIR))
    e.append(pill(fx + 52, 220, "AUTHORING · nide", NAVY3, 8.5))
    e.append(text(fx + 16, 250, "nide quality", 12, INK, 600, font=MONO))
    e.append(text(fx + 16, 270, "OASIS-MEMBER-URI", 10, NAVY3, 600, font=MONO))
    e.append(rect(fx, 308, 210, 96, SURF2, BORDER, HAIR))
    e.append(pill(fx + 46, 332, "INTAKE · pub-check", RED, 8.5))
    e.append(text(fx + 16, 362, "member-uri", 12, INK, 600, font=MONO))
    e.append(text(fx + 16, 382, "BLOCKER at the gate", 10, RED, 600, font=MONO))
    e.append(text(fx, 424, "same rule, both gates", 10, MUTED))

    # summary bar
    by = 466
    e.append(rect(56, by, W - 112, 82, NAVY_T, NAVY3, HAIR, r=3))
    e.append(text(76, by + 32, "38 of 164 checks cite a written clause like this one.",
                  13, INK, 600))
    e.append(text(76, by + 56, "The rest are operational rules earned from a year of published "
                               "corrections. The full criterion-to-clause map is AUTHORITIES.md.",
                  11.5, BODY))

    e.append("</svg>")
    write(OUT / "authority.svg", e)


# ===========================================================================
# architecture/nide-bridge.svg (1240 x 640)  how pub-check dovetails with nide
# ===========================================================================
def build_nide_bridge():
    W, H = 1240, 640
    e = [svg_open(W, H), marker_defs(), canvas(W, H)]
    e.append(oasis_logo(W - 196, 42, 140))
    e.append(kicker(56, 52, "Interoperation · authoring meets intake"))
    e.append(text(56, 86, "How pub-check dovetails with nide", 26, INK, 700))
    e.append(text(56, 112, "The TC authors and self-checks with Stefan Hagen’s nide; OASIS "
                           "verifies and publishes with pub-check.", 12.5, MUTED))
    e.append(text(56, 131, "They share one rules file and one manifest, so a green authoring "
                           "run predicts a green intake run.", 12.5, MUTED))

    ly, lh = 178, 300
    midy = ly + lh / 2

    # ---- LEFT lane: nide (Stefan / TC authoring) ----
    lx, lw = 48, 372
    e.append(rect(lx, ly, lw, lh, NAVY_T, NAVY3, EMPH, r=3))
    e.append(text(lx + 22, ly + 34, "nide", 18, INK, 700, font=MONO))
    e.append(text(lx + 22, ly + 54, "TC SIDE · AUTHORING (Stefan Hagen)", 9.5, NAVY3, 600, ls=1))
    e.append(rule(lx + 22, ly + 66, lx + lw - 22, ly + 66, NAVY3, HAIR))
    nrows = [
        ("assemble · render", "md source → html + pdf (pandoc, typst)"),
        ("quality", "reads oasis.rules.yaml, fails on any BLOCKER"),
        ("manifest", "emits nide-manifest 1.0 (sha256 + blake3)"),
    ]
    for i, (a, b) in enumerate(nrows):
        ry0 = ly + 86 + i * 68
        e.append(rect(lx + 20, ry0, lw - 40, 56, SURFACE, BORDER, HAIR))
        e.append(text(lx + 34, ry0 + 24, a, 12.5, INK, 600, font=MONO))
        e.append(text(lx + 34, ry0 + 43, b, 10.5, BODY))

    # ---- RIGHT lane: pub-check (OASIS intake) ----
    rx, rw = 820, 372
    e.append(rect(rx, ly, rw, lh, ACC_T, ACCENT, EMPH, r=3))
    e.append(text(rx + 22, ly + 34, "pub-check", 18, INK, 700, font=MONO))
    e.append(text(rx + 22, ly + 54, "OASIS SIDE · INTAKE GATE", 9.5, ACCENT, 600, ls=1))
    e.append(rule(rx + 22, ly + 66, rx + rw - 22, ly + 66, ACCENT, HAIR))
    prows = [
        ("164 checks / 55 classes", "the delivered package, gated"),
        ("verify", "delivered PDF bytes vs manifest hashes"),
        ("exit 0 · publish   exit 1 · back to TC", "intake accepts with the same rules"),
    ]
    for i, (a, b) in enumerate(prows):
        ry0 = ly + 86 + i * 68
        e.append(rect(rx + 20, ry0, rw - 40, 56, SURFACE, BORDER, HAIR))
        e.append(text(rx + 34, ry0 + 24, a, 11.5 if i == 2 else 12.5, INK, 600, font=MONO))
        e.append(text(rx + 34, ry0 + 43, b, 10.5, BODY))

    # ---- MIDDLE seam: the two shared artifacts + directional flows ----
    mcx = (lx + lw + rx) / 2  # centre of the gap
    # top artifact: shared rules (flows OASIS -> nide, back-flow)
    aw, ah = 300, 92
    ax = mcx - aw / 2
    ry_rules = 196
    e.append(rect(ax, ry_rules, aw, ah, SURFACE, BORDER2, EMPH))
    e.append(text(mcx, ry_rules + 26, "oasis.rules.yaml", 12.5, INK, 700, anchor="middle", font=MONO))
    e.append(text(mcx, ry_rules + 46, "16 org rules · authored by OASIS", 10, MUTED, anchor="middle"))
    e.append(text(mcx, ry_rules + 64, "nide pulls via  extends: oasis", 10, NAVY3, 600, anchor="middle", font=MONO))
    e.append(text(mcx, ry_rules + 82, "read by BOTH gates", 9.5, MUTED, anchor="middle"))
    # back-flow arrows (right -> left): pub-check publishes -> rules -> nide reads
    e.append(arrow(rx - 8, ry_rules + 22, ax + aw + 8, ry_rules + 22, ACCENT, 1.5, "aAcc"))
    e.append(text((rx + ax + aw) / 2, ry_rules + 14, "OASIS publishes", 9, ACCENT, 600, anchor="middle"))
    e.append(arrow(ax - 8, ry_rules + 22, lx + lw + 8, ry_rules + 22, NAVY3, 1.5, "aNavy"))
    e.append(text((lx + lw + ax) / 2, ry_rules + 14, "nide reads", 9, NAVY3, 600, anchor="middle"))

    # bottom artifact: package + manifest (flows nide -> pub-check, forward-flow)
    ry_pkg = 388
    e.append(rect(ax, ry_pkg, aw, ah, SURFACE, BORDER2, EMPH))
    e.append(text(mcx, ry_pkg + 26, "delivery package", 12.5, INK, 700, anchor="middle"))
    e.append(text(mcx, ry_pkg + 45, "md · html · pdf · schemas", 10, MUTED, anchor="middle", font=MONO))
    e.append(text(mcx, ry_pkg + 66, "+ nide-manifest 1.0", 11, ACCENT, 700, anchor="middle", font=MONO))
    e.append(text(mcx, ry_pkg + 83, "provenance: source · outputs · toolchain", 9.5, MUTED, anchor="middle"))
    # forward-flow arrows (left -> right): nide emits -> pkg -> pub-check verifies
    e.append(arrow(lx + lw + 8, ry_pkg + 22, ax - 8, ry_pkg + 22, NAVY3, 1.5, "aNavy"))
    e.append(text((lx + lw + ax) / 2, ry_pkg + 14, "nide emits", 9, NAVY3, 600, anchor="middle"))
    e.append(arrow(ax + aw + 8, ry_pkg + 22, rx - 8, ry_pkg + 22, ACCENT, 1.5, "aAcc"))
    e.append(text((rx + ax + aw) / 2, ry_pkg + 14, "pub-check verifies", 9, ACCENT, 600, anchor="middle"))

    # dovetail joint glyph between the two artifacts (the interlock)
    jy = ry_rules + ah + 6
    tab = f'{mcx-46},{jy} {mcx+46},{jy} {mcx+30},{ry_pkg-6} {mcx-30},{ry_pkg-6}'
    e.append(f'<polygon points="{tab}" fill="#c9d6f8" stroke="{ACCENT}" stroke-width="1.3"/>')
    e.append(text(mcx, (jy + ry_pkg) / 2 + 4, "the dovetail", 9.5, ACCENT, 600, anchor="middle"))

    # ---- takeaway bar ----
    by = 502
    e.append(rect(56, by, W - 112, 96, SURF2, BORDER2, HAIR, r=3))
    e.append(text(76, by + 30, "One rules file, one manifest, two gates.", 13.5, INK, 700))
    e.append(text(76, by + 54, "The rules are authored by OASIS and pulled by nide, so both gates "
                               "check the same source rules: a green  nide quality  run predicts a green intake.", 11.5, BODY))
    e.append(text(76, by + 74, "The manifest is emitted by nide and hash-verified at intake, so the "
                               "published bytes are provably the build the TC voted on.", 11.5, BODY))

    e.append("</svg>")
    write(ARCH / "nide-bridge.svg", e)


# ===========================================================================
def render_pngs():
    targets = [OUT / "hero.svg", OUT / "gate.svg", OUT / "pipeline.svg",
               OUT / "chain.svg", ARCH / "validation-audit-dovetail.svg",
               ARCH / "two-layer-stack.svg", OUT / "authority.svg", ARCH / "nide-bridge.svg"]
    for t in targets:
        png = t.with_suffix(".png")
        subprocess.run(["rsvg-convert", "-z", "2", str(t), "-o", str(png)], check=True)
        print(f"rendered {png.name}")


if __name__ == "__main__":
    build_hero()
    build_gate()
    build_pipeline()
    build_chain()
    build_dovetail()
    build_stack()
    build_authority()
    build_nide_bridge()
    if "--png" in sys.argv:
        render_pngs()
