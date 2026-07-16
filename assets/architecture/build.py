#!/usr/bin/env python3
"""Generate the two OASIS publication-quality architecture SVGs.

1. validation-audit-dovetail.svg  (1400x900 landscape, flagship)
2. two-layer-stack.svg            (900x1100 portrait, slide summary)

Hand-authored geometry, self-contained, no external refs. Arial/Helvetica only,
no emojis, no em dashes. OASIS palette with one teal accent for the dovetail joint.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent

# ---- palette -------------------------------------------------------------
NAVY     = "#1B3A5C"
BLUE     = "#0B5CAD"
BLUE_MID = "#2C6FB0"
TEAL     = "#149C9F"
TEAL_DK  = "#0E7B7E"
TEAL_LT  = "#E6F6F5"
WHITE    = "#FFFFFF"
INK      = "#243B4F"
SUB      = "#4A6076"
PANEL_L  = "#F4F8FC"
PANEL_R  = "#F3F6F9"
STROKE_L = "#B8CEDF"
STROKE_R = "#B4C4D2"
AMBER    = "#D98A00"
RED      = "#C0392B"
CHIP_BG  = "#FFFFFF"
CHIP_STK = "#8FB0C9"
FAM      = "Arial, Helvetica, sans-serif"


# ---- helpers -------------------------------------------------------------
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def rrect(x, y, w, h, r, fill, stroke="none", sw=0):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke != "none" else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" fill="{fill}"{s}/>'


def top_round(x, y, w, h, r, fill):
    return (f'<path d="M{x+r},{y} H{x+w-r} A{r},{r} 0 0 1 {x+w},{y+r} '
            f'V{y+h} H{x} V{y+r} A{r},{r} 0 0 1 {x+r},{y} Z" fill="{fill}"/>')


def txt(x, y, s, size, fill=INK, weight="normal", anchor="middle",
        spacing=None, ls=None):
    sp = f' letter-spacing="{spacing}"' if spacing is not None else ""
    return (f'<text x="{x}" y="{y}" font-family="{FAM}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>'
            f'{esc(s)}</text>')


def doc_shape(x, y, w, h, fold, fill, stroke, sw):
    body = (f'<path d="M{x},{y} H{x+w-fold} L{x+w},{y+fold} V{y+h} H{x} Z" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    tri = (f'<path d="M{x+w-fold},{y} L{x+w},{y+fold} H{x+w-fold} Z" '
           f'fill="#D6E6F5" stroke="{stroke}" stroke-width="{sw}"/>')
    return body + tri


def arrow(x1, y1, x2, y2, color=NAVY, sw=2.2, marker="arrN"):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="{sw}" marker-end="url(#{marker})"/>')


def path_arrow(d, color=NAVY, sw=2.2, marker="arrN"):
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'marker-end="url(#{marker})"/>')


def badge(cx, y, w, h, label, fill):
    x = cx - w / 2
    return (rrect(x, y, w, h, h / 2, fill) +
            txt(cx, y + h / 2 + 3.2, label, 9, WHITE, "bold"))


def dash_rect(x, y, w, h, r, stroke, sw=1.4, fill=WHITE):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-dasharray="5 4"/>')


def tick(x, y, s, color, size=12, bold=False, ink=INK):
    return (f'<circle cx="{x}" cy="{y-4}" r="3.4" fill="{color}"/>' +
            txt(x+14, y, s, size, ink, "bold" if bold else "normal", anchor="start"))


def defs():
    def marker(mid, color):
        return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')
    return ('<defs>' + marker("arrN", NAVY) + marker("arrT", TEAL_DK) +
            marker("arrB", BLUE) + marker("arrG", "#B7C6D2") +
            marker("arrW", WHITE) + marker("arrSL", "#5F7B96") + '</defs>')


# =========================================================================
# SVG 1 : validation-audit-dovetail.svg
# =========================================================================
def build_dovetail():
    W, H = 1400, 900
    e = []
    e.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="{FAM}">')
    e.append(defs())
    e.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{WHITE}"/>')
    e.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" fill="none" '
             f'stroke="#DCE4EC" stroke-width="1"/>')

    # --- title ---
    e.append(txt(W/2, 42, "Publication Quality Architecture: How the Two Layers Dovetail",
                 27, NAVY, "bold"))
    e.append(txt(W/2, 68,
                 "One validation engine (pub-check) runs on both sides; the human audit wraps it with gates the tool cannot see",
                 13.5, SUB))

    # --- lane panels ---
    LY, LH = 95, 665
    e.append(rrect(40, LY, 520, LH, 14, PANEL_L, STROKE_L, 1.5))          # left
    e.append(rrect(840, LY, 520, LH, 14, PANEL_R, STROKE_R, 1.5))         # right

    # left header
    e.append(top_round(40, LY, 520, 50, 14, BLUE))
    e.append(txt(300, LY+21, "LAYER 1  ·  VALIDATION  ·  TC SIDE", 15, WHITE, "bold", spacing=0.6))
    e.append(txt(300, LY+40, "Stefan Hagen / TC editor:  “Is the DOCUMENT ready?”", 12, "#D6E6F5"))
    # right header
    e.append(top_round(840, LY, 520, 50, 14, NAVY))
    e.append(txt(1100, LY+21, "LAYER 2  ·  PUBLICATION AUDIT  ·  TC ADMINISTRATION SIDE", 15, WHITE, "bold", spacing=0.4))
    e.append(txt(1100, LY+40, "The publication event: “Did WE publish it right?”", 12, "#C9D6E2"))

    # ---------------- LEFT column content ----------------
    lcx = 300
    # Box A package
    e.append(rrect(60, 165, 480, 96, 10, WHITE, BLUE, 2))
    e.append(txt(lcx, 189, "PACKAGE ASSEMBLED", 14, NAVY, "bold", spacing=0.5))
    e.append(txt(lcx, 210, "filenames  ·  case  ·  front matter  ·  anchors", 11.5, SUB))
    e.append(txt(lcx, 228, "fonts  ·  placeholders  ·  schema $id  ·  stage naming", 11.5, SUB))
    e.append(txt(lcx, 246, "image policy  ·  junk files", 11.5, SUB))
    e.append(arrow(lcx, 261, lcx, 296))
    # Box B run in CI
    e.append(rrect(60, 300, 480, 110, 10, WHITE, BLUE, 2))
    e.append(txt(lcx, 328, "RUN pub-check IN THE TC's OWN CI", 14.5, NAVY, "bold"))
    e.append(txt(lcx, 350, "before submission, no review round-trip", 12, SUB))
    e.append(txt(lcx, 370, "the TC can run the exact gate we run", 12, SUB))
    e.append(txt(lcx, 392, "the TC owns “the document is ready”", 12, TEAL_DK, "bold"))
    e.append(arrow(lcx, 410, lcx, 462))
    # Box C validation report
    e.append(doc_shape(76, 464, 448, 92, 22, WHITE, BLUE, 2))
    e.append(txt(296, 490, "VALIDATION REPORT", 14, BLUE, "bold", spacing=0.5))
    e.append(txt(296, 512, "all 92 conditions: observed vs expected, in full", 11.5, SUB))
    e.append(txt(296, 532, "zero blockers  =  publication-ready package", 11.5, INK, "bold"))
    e.append(arrow(300, 556, 300, 596))
    e.append(rrect(120, 598, 360, 40, 20, BLUE))
    e.append(txt(300, 623, "SUBMIT PACKAGE TO TC ADMINISTRATION", 13, WHITE, "bold"))

    # ---------------- RIGHT column content ----------------
    rcx = 1100
    # intake
    e.append(rrect(860, 165, 480, 52, 10, WHITE, NAVY, 1.6))
    e.append(txt(rcx, 189, "INTAKE", 13.5, NAVY, "bold", spacing=0.5))
    e.append(txt(rcx, 207, "package + Validation Report received by TC Administration", 11.5, SUB))
    e.append(arrow(rcx, 217, rcx, 297))
    # Gate 4b (dovetail socket, teal)
    e.append(rrect(860, 300, 480, 110, 10, TEAL_LT, TEAL, 2.6))
    e.append(txt(rcx, 328, "AUDIT GATE 4b  ·  THE DOVETAIL JOINT", 14.5, TEAL_DK, "bold"))
    e.append(txt(rcx, 350, "re-run pub-check + triage every finding", 12, INK))
    e.append(txt(rcx, 370, "the whole 92-check validation layer plugs in here", 12, INK))
    e.append(txt(rcx, 392, "trust, but verify:  identical code, our side", 12, TEAL_DK, "bold"))

    # subheader for other gates
    e.append(txt(rcx, 438, "GATES ONLY A HUMAN / LIVE CHECK CAN DO", 13, NAVY, "bold", spacing=0.4))
    e.append(txt(rcx, 455, "live ground truth pub-check never sees", 11, SUB))

    # chip grid (3 columns)
    chips = [
        "GitHub vs LIVE byte identity",
        "Render class vs TC precedent",
        "Front matter vs LIVE roster",
        "Current Naming Directives",
        "LIVE directory index chain",
        "Zip integrity",
        "4 announcement channels",
        "TCADMIN ticket record",
        "Visual eyeball of LIVE page",
    ]
    gx0, gy0 = 860, 468
    cw, ch, gapx, gapy = 152, 50, 12, 12
    for i, c in enumerate(chips):
        col = i % 3
        row = i // 3
        cx = gx0 + col * (cw + gapx)
        cy = gy0 + row * (ch + gapy)
        e.append(rrect(cx, cy, cw, ch, 7, CHIP_BG, CHIP_STK, 1.4))
        # tiny teal tick
        e.append(f'<circle cx="{cx+14}" cy="{cy+ch/2}" r="4" fill="{TEAL}"/>')
        # wrap label into up to 2 lines
        words = c.split(" ")
        if len(c) > 17 and len(words) > 2:
            mid = len(words) // 2
            l1 = " ".join(words[:mid]); l2 = " ".join(words[mid:])
            e.append(txt(cx+26, cy+ch/2-2, l1, 10.5, INK, "bold", anchor="start"))
            e.append(txt(cx+26, cy+ch/2+14, l2, 10.5, INK, "bold", anchor="start"))
        else:
            e.append(txt(cx+26, cy+ch/2+4, c, 10.5, INK, "bold", anchor="start"))

    # wide chip: adversarial verifier (row 4, spans)
    wy = gy0 + 3 * (ch + gapy)
    e.append(rrect(860, wy, cw*3+gapx*2, ch-4, 7, "#FBF4E8", AMBER, 1.6))
    e.append(f'<circle cx="{874}" cy="{wy+(ch-4)/2}" r="4" fill="{AMBER}"/>')
    e.append(txt(886, wy+(ch-4)/2+4, "Independent adversarial verifier agent  ·  refute mandate",
                 11, "#7A5200", "bold", anchor="start"))

    # audit report artifact
    ary = wy + (ch-4) + 14
    e.append(doc_shape(876, ary, 448, 60, 20, WHITE, NAVY, 2))
    e.append(txt(1096, ary+24, "PUBLICATION AUDIT REPORT", 13.5, NAVY, "bold", spacing=0.4))
    e.append(txt(1096, ary+44, "15-16 gate table, verdict computed not asserted", 11, SUB))
    e.append(arrow(1100, ary+60, 1100, 792, sw=2.2))

    # ---------------- CENTER shared engine ----------------
    ex, ey, ew, eh = 592, 296, 216, 168
    ecx = ex + ew/2  # 700
    emid = ey + eh/2
    # dovetail tabs first (behind engine edges); flare outward = joint
    lt = f'{ex},{ey+44} {ex-40},{ey+34} {ex-40},{ey+eh-34} {ex},{ey+eh-44}'
    e.append(f'<polygon points="{lt}" fill="{TEAL}" stroke="{TEAL_DK}" stroke-width="1.5"/>')
    rt = f'{ex+ew},{ey+44} {ex+ew+40},{ey+34} {ex+ew+40},{ey+eh-34} {ex+ew},{ey+eh-44}'
    e.append(f'<polygon points="{rt}" fill="{TEAL}" stroke="{TEAL_DK}" stroke-width="1.5"/>')
    # small directional arrows across the seams, on the tabs
    e.append(arrow(ex-32, emid, ex-8, emid, WHITE, 2.2, "arrT"))
    e.append(arrow(ex+ew+8, emid, ex+ew+32, emid, WHITE, 2.2, "arrT"))
    # engine body
    e.append(rrect(ex, ey, ew, eh, 12, TEAL_LT, TEAL, 3))
    e.append(top_round(ex, ey, ew, 30, 12, TEAL))
    e.append(txt(ecx, ey+20, "pub-check", 16, WHITE, "bold", spacing=0.5))
    e.append(txt(ecx, ey+48, "pub_check.py", 12.5, TEAL_DK, "bold"))
    e.append(txt(ecx, ey+67, "92 individual checks", 11.5, INK))
    e.append(txt(ecx, ey+84, "34 check classes", 11.5, INK))
    e.append(f'<line x1="{ex+18}" y1="{ey+94}" x2="{ex+ew-18}" y2="{ey+94}" stroke="{TEAL}" stroke-width="1" stroke-dasharray="3 3"/>')
    # badges
    e.append(badge(ecx-64, ey+102, 56, 17, "BLOCKER", RED))
    e.append(badge(ecx, ey+102, 44, 17, "WARN", AMBER))
    e.append(badge(ecx+58, ey+102, 44, 17, "INFO", BLUE_MID))
    e.append(txt(ecx, ey+139, "sees ONLY the package files,", 10, SUB))
    e.append(txt(ecx, ey+153, "never the live site", 10, SUB))

    # banner above engine
    e.append(rrect(ecx-118, ey-32, 236, 22, 11, NAVY))
    e.append(txt(ecx, ey-16.5, "IDENTICAL CODE, BOTH SIDES", 11, WHITE, "bold", spacing=0.5))

    # tab labels, clear below the engine, at the seams
    e.append(txt(ex+8, ey+eh+22, "run in TC CI", 10.5, TEAL_DK, "bold"))
    e.append(txt(ex+ew-13, ey+eh+22, "re-run at intake", 10.5, TEAL_DK, "bold"))

    # ---------------- submit -> intake handoff connector ----------------
    # routes up the left lane's right padding (boxes end by x=540), across
    # above the engine banner (banner top y=264), then up into intake's base.
    e.append(path_arrow("M480,618 H548 V244 H1000 V219", "#5F7B96", 1.8, "arrSL"))
    e.append(txt(792, 238, "submitted package", 10.5, "#5F7B96"))

    # ---------------- bottom band : ticket ----------------
    e.append(rrect(545, 792, 310, 76, 12, NAVY))
    e.append(txt(700, 820, "TCADMIN TICKET  +  _audit/  REPO", 14, WHITE, "bold", spacing=0.3))
    e.append(txt(700, 842, "both standard reports filed here", 11.5, "#C9D6E2"))
    e.append(txt(700, 858, "the shared record of the publication", 10.5, "#9FB4C6"))
    # converging arrows
    e.append(path_arrow(f"M300,638 V830 H540", NAVY, 2.2))
    e.append(path_arrow(f"M1100,792 V830 H860", NAVY, 2.2))
    # labels on the converging arrows
    e.append(txt(420, 823, "Validation Report", 10.5, SUB, anchor="middle"))
    e.append(txt(980, 823, "Audit Report", 10.5, SUB, anchor="middle"))

    e.append('</svg>')
    (OUT / "validation-audit-dovetail.svg").write_text("\n".join(e))
    print("wrote validation-audit-dovetail.svg")


# =========================================================================
# SVG 2 : two-layer-stack.svg  (900 x 1100 portrait)
# =========================================================================
def build_stack():
    W, H = 900, 1100
    e = []
    e.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="{FAM}">')
    e.append(defs())
    e.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{WHITE}"/>')
    e.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" fill="none" '
             f'stroke="#DCE4EC" stroke-width="1"/>')

    # title
    e.append(txt(W/2, 46, "The OASIS Publication Quality Stack", 26, NAVY, "bold"))
    e.append(txt(W/2, 74,
                 "Package in at the bottom, verified publication at the top; two layers joined at gate 4b",
                 13, SUB))

    # left flow spine (subtle, background)
    e.append(arrow(32, 1010, 32, 300, "#C6D4DE", 4, "arrG"))
    e.append(f'<text transform="rotate(-90 50 655)" x="50" y="655" '
             f'font-family="{FAM}" font-size="11" fill="#9AAEBE" '
             f'text-anchor="middle" letter-spacing="1.5">PUBLICATION READINESS</text>')

    # -------- PACKAGE IN (bottom) --------
    e.append(rrect(250, 980, 400, 72, 14, WHITE, BLUE, 2))
    e.append(txt(450, 1012, "PACKAGE IN", 16, NAVY, "bold", spacing=0.5))
    e.append(txt(450, 1034, "the assembled TC submission package", 12, SUB))
    e.append(arrow(450, 980, 450, 960))

    # -------- LAYER 1 : VALIDATION --------
    e.append(rrect(60, 735, 780, 220, 14, TEAL_LT, TEAL, 2.5))
    e.append(top_round(60, 735, 780, 40, 14, TEAL))
    e.append(txt(450, 760, "LAYER 1  ·  VALIDATION  ·  pub-check (mechanical, tool-side)",
                 15, WHITE, "bold", spacing=0.3))
    # left content
    e.append(txt(95, 808, "pub_check.py:  92 checks across 34 classes", 13.5, NAVY, "bold", anchor="start"))
    e.append(txt(95, 832, "Runs in the TC's own CI before submission.", 12, SUB, anchor="start"))
    e.append(txt(95, 854, "Re-run identically by TC Administration at gate 4b.", 12, SUB, anchor="start"))
    e.append(txt(95, 878, "Every finding gets a severity:", 12, SUB, anchor="start"))
    e.append(badge(140, 890, 56, 18, "BLOCKER", RED))
    e.append(badge(213, 890, 46, 18, "WARN", AMBER))
    e.append(badge(275, 890, 46, 18, "INFO", BLUE_MID))
    e.append(txt(95, 936, "Output: a Validation Report, observed vs expected for all 92.",
                 12, TEAL_DK, "bold", anchor="start"))
    # right annotation panel
    e.append(dash_rect(500, 793, 315, 148, 10, TEAL))
    e.append(txt(514, 817, "WHAT THE TOOL SEES", 12.5, TEAL_DK, "bold", anchor="start", spacing=0.4))
    for i, s in enumerate(["filenames  ·  case  ·  front matter",
                            "anchors  ·  fonts  ·  placeholders",
                            "schema $id  ·  stage naming",
                            "image policy  ·  junk files"]):
        e.append(txt(514, 843 + i*20, s, 11.5, INK, anchor="start"))
    e.append(txt(514, 928, "only the package, never the live site", 10.5, "#7A8C99", anchor="start"))

    # -------- LAYER 2 : AUDIT --------
    e.append(rrect(60, 300, 780, 390, 14, PANEL_R, NAVY, 2.5))
    e.append(top_round(60, 300, 780, 40, 14, NAVY))
    e.append(txt(450, 325, "LAYER 2  ·  PUBLICATION AUDIT  ·  human + adversarial (event-side)",
                 15, WHITE, "bold", spacing=0.2))
    # left gate list
    gates = [
        ("Gate 4b: run pub-check + triage findings  (the dovetail)", TEAL, True, TEAL_DK),
        ("GitHub vs LIVE byte identity", NAVY, False, INK),
        ("Render class vs the TC's own precedent", NAVY, False, INK),
        ("Front matter vs the LIVE roster", NAVY, False, INK),
        ("Current Naming Directives", NAVY, False, INK),
        ("LIVE directory index chain", NAVY, False, INK),
        ("Zip integrity", NAVY, False, INK),
        ("Four announcement channels at destination", NAVY, False, INK),
        ("TCADMIN ticket record", NAVY, False, INK),
        ("Independent adversarial verifier (refute mandate)", NAVY, False, INK),
        ("Visual eyeball of the LIVE page", NAVY, False, INK),
    ]
    for i, (s, col, bold, ink) in enumerate(gates):
        e.append(tick(98, 374 + i*27, s, col, 12, bold, ink))
    # right annotation panel
    e.append(dash_rect(500, 360, 315, 250, 10, NAVY))
    e.append(txt(514, 384, "WHAT ONLY A HUMAN /", 12.5, NAVY, "bold", anchor="start", spacing=0.3))
    e.append(txt(514, 402, "LIVE CHECK CAN SEE", 12.5, NAVY, "bold", anchor="start", spacing=0.3))
    e.append(txt(514, 430, "Live ground truth the tool", 11.5, INK, anchor="start"))
    e.append(txt(514, 448, "cannot reach:", 11.5, INK, anchor="start"))
    for i, s in enumerate(["the running site",
                            "the roster as it stands today",
                            "the four destinations",
                            "the rendered page",
                            "an adversary set to refute it"]):
        e.append(tick(520, 476 + i*24, s, NAVY, 11.5))
    # explanatory line above the joint
    e.append(txt(450, 668, "Gate 4b requires running pub-check and triaging every finding.",
                 12, SUB))

    # -------- dovetail joint (validation top -> audit bottom) --------
    tab = "400,735 500,735 515,693 385,693"
    e.append(f'<polygon points="{tab}" fill="{TEAL}" stroke="{TEAL_DK}" stroke-width="1.5"/>')
    e.append(arrow(450, 733, 450, 723, WHITE, 2.4, "arrW"))
    e.append(rrect(372, 697, 156, 22, 11, TEAL_DK))
    e.append(txt(450, 712, "GATE 4b  ·  DOVETAIL", 11, WHITE, "bold", spacing=0.4))

    # -------- PUBLISHED (top) --------
    e.append(rrect(140, 130, 620, 150, 16, NAVY))
    e.append(f'<circle cx="212" cy="205" r="34" fill="{TEAL}"/>')
    e.append(f'<path d="M196,205 l11,12 l21,-24" fill="none" stroke="{WHITE}" '
             f'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
    e.append(txt(480, 182, "PUBLISHED + VERIFIED PUBLICATION", 18, WHITE, "bold", spacing=0.3))
    e.append(txt(480, 212, "live on docs.oasis-open.org", 13, "#CBD8E6"))
    e.append(txt(480, 236, "all four channels announced", 12, "#A6BACB"))
    e.append(txt(480, 258, "audit report filed to the ticket and _audit/", 12, "#A6BACB"))
    e.append(arrow(450, 300, 450, 282))

    e.append('</svg>')
    (OUT / "two-layer-stack.svg").write_text("\n".join(e))
    print("wrote two-layer-stack.svg")


if __name__ == "__main__":
    build_dovetail()
    build_stack()
