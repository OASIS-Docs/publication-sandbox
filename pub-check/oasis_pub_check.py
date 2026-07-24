#!/usr/bin/env python3
# Copyright 2025-2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""oasis_pub_check: the OASIS publication acceptance criteria, executable for TC work-product packages.

Validation is on the output. All roads lead to HTML and PDF: whatever the
authoring format (Markdown, Word, DocBook/XML, LaTeX, ...), the published form
is HTML + PDF at the canonical URLs, and the bulk of the gate runs on those
outputs for every package. Source-format checks are add-ons applied to
whatever source the package carries: markdown add-ons for .md, Word
render-fidelity add-ons for .docx. Source-only checks never false-fire on a
package that lacks that source.

Runs the checks TC Administration applies to a submitted work-product package
BEFORE publication to docs.oasis-open.org, so a TC can run them in its own
build (make target, CI job, pre-vote gate) and submit packages that publish
without a review round-trip.

Every check corresponds to a finding that has actually bounced or delayed a
real submission. Stdlib only. No configuration file: everything is derived
from the package itself.

Usage:
    oasis_pub_check.py <stage-dir | package.zip> [--json] [--emit-manifest]

The stage directory is the directory that will be published, e.g.
    openeox/eox-core/v1.0/csd01/
containing the delivery items (.md, .html, .pdf) and any schema/ subtree.

Exit status: 0 = publishable (warnings allowed), 1 = blockers found.

Author: Michael Coletta, Technical Advisor to OASIS Open.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from html.parser import HTMLParser

__author__ = "Michael Coletta <michael.coletta@oasis-open.org>"

SITE = "https://docs.oasis-open.org"

# Naming Directives (current, since v1.7 of 2 Jan 2024): a document in public
# review KEEPS its stage name. csprd/cnprd/cos are retired; csdpr never existed.
VALID_STAGE_PREFIXES = {"wd", "csd", "cs", "cnd", "cn", "os", "ps", "psd", "pn", "pnd", "errata"}
RETIRED_STAGE_TOKENS = {"csprd", "cnprd", "cos", "csdpr", "cndpr"}

BLOCKER, WARN, INFO = "BLOCKER", "WARN", "INFO"


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.observed: dict[str, dict[str, str]] = {}

    def add(self, severity: str, check: str, message: str) -> None:
        self.items.append({"severity": severity, "check": check, "message": message})

    def observe(self, check: str, **kv) -> None:
        """Record the concrete values a check pulled from the package, so a
        validation report can show observed-vs-expected for conditions that
        PASS (a silent pass is unreviewable). Values are stringified in full,
        never truncated: the observed value is the evidence the report exists
        to show. Lists join with commas."""
        slot = self.observed.setdefault(check, {})
        for k, v in kv.items():
            if isinstance(v, (list, tuple, set)):
                v = ", ".join(str(x) for x in sorted(v)) if v else "(none)"
            slot[k] = str(v)

    @property
    def blockers(self) -> int:
        return sum(1 for f in self.items if f["severity"] == BLOCKER)


class _AnchorParser(HTMLParser):
    """Collect element ids, <a name=...>, internal hrefs, and the <title>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.internal_hrefs: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        if tag == "a" and "name" in d:
            self.ids.add(d["name"])
        if tag == "a" and d.get("href", "").startswith("#"):
            self.internal_hrefs.append(d["href"][1:])
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def strip_code_blocks(text: str, kind: str) -> str:
    """Blank out fenced/code content so residue and link checks only see prose.
    Replacement preserves line numbers."""

    def blank(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")

    if kind == "md":
        text = re.sub(r"^(```|~~~).*?^\1\s*$", blank, text, flags=re.M | re.S)
        text = re.sub(r"(?<!`)`[^`\n]+`(?!`)", " ", text)
    else:
        text = re.sub(r"<pre\b.*?</pre>", blank, text, flags=re.S | re.I)
        text = re.sub(r"<code\b.*?</code>", blank, text, flags=re.S | re.I)
    return text


def find_delivery_items(stage_dir: str,
                        exts: tuple[str, ...] = ("md", "html", "pdf")) -> dict[str, str]:
    """Map extension -> path for the DELIVERY items in dir root.

    A stage directory legitimately carries auxiliary artifacts next to the
    delivery items (comment-resolution logs, -DIFF PDFs, public-review
    metadata, namespace pages). The delivery item per format is the file
    whose stem ends in -<stage>; if none does, fall back to the shortest
    stem (covers pre-rename working packages so the filename check can
    report them). The default extension set is the markdown track; the
    DOCX-native track asks for (docx, html, pdf)."""
    stage = os.path.basename(os.path.normpath(stage_dir))
    cands: dict[str, list[str]] = {e: [] for e in exts}
    for name in sorted(os.listdir(stage_dir)):
        p = os.path.join(stage_dir, name)
        if not os.path.isfile(p):
            continue
        ext = os.path.splitext(name)[1].lstrip(".").lower()
        if ext in cands:
            cands[ext].append(p)
    out: dict[str, str] = {}
    for ext, paths in cands.items():
        if not paths:
            continue
        exact = [p for p in paths
                 if os.path.splitext(os.path.basename(p))[0].endswith(f"-{stage}")]
        pool = exact or paths
        out[ext] = min(pool, key=lambda p: len(os.path.basename(p)))
    return out


def auxiliary_files(stage_dir: str, items: dict[str, str]) -> list[str]:
    delivery = {os.path.basename(p) for p in items.values()}
    out = []
    for name in sorted(os.listdir(stage_dir)):
        if os.path.isfile(os.path.join(stage_dir, name)) and name not in delivery:
            out.append(name)
    return out


def parse_stage(stage_dir: str) -> tuple[str, str]:
    """Return (version, stage). The version is the nearest ancestor directory
    matching vN.N, so errata paths (.../v2.0/errata01/os) parse correctly."""
    norm = os.path.normpath(stage_dir)
    stage = os.path.basename(norm)
    version = os.path.basename(os.path.dirname(norm))
    probe = os.path.dirname(norm)
    while probe and os.path.basename(probe):
        if re.fullmatch(r"v\d+(\.\d+)+", os.path.basename(probe)):
            version = os.path.basename(probe)
            break
        probe = os.path.dirname(probe)
    return version, stage


def stage_urls_from_md(md_text: str, heading: str) -> list[str]:
    """URLs under a front-matter heading. 'This' matches This Stage/This Version
    (the template wording changed); same for 'Latest'."""
    m = re.search(rf"^#+ {heading} (?:Stage|Version)\b.*?$(.*?)^#+ ",
                  md_text, re.M | re.S | re.I)
    if not m:
        return []
    return re.findall(r"https?://\S+?(?=[)\s\\]|$)", m.group(1))


# ---------------------------------------------------------------- checks

def check_stage_name(stage: str, f: Findings) -> None:
    m = re.fullmatch(r"([a-z]+)(\d\d)?", stage)
    prefix = m.group(1) if m else stage
    if m and prefix in VALID_STAGE_PREFIXES and prefix != "os" and not m.group(2):
        f.add(BLOCKER, "stage-name",
              f"Stage '{stage}' is missing its two-digit number (e.g. {prefix}01).")
    if prefix in RETIRED_STAGE_TOKENS:
        f.add(BLOCKER, "stage-name",
              f"Stage '{stage}' uses a retired/invalid stage token. Current naming: a document "
              f"in public review keeps its stage name (csd stays csd). Valid: "
              f"{', '.join(sorted(VALID_STAGE_PREFIXES))} + two digits.")
    elif prefix not in VALID_STAGE_PREFIXES:
        f.add(BLOCKER, "stage-name", f"Stage '{stage}' is not a recognized stage token.")


def check_version_naming(version: str, stem: str, f: Findings) -> None:
    """Naming Directives: the version directory is vN.N(.N) and the delivery
    stem carries it (<base>-v<X.Y>-<stage>). A stem whose embedded version
    disagrees with the directory is a stale-rename tell."""
    if not re.fullmatch(r"v\d+(\.\d+)+", version):
        f.add(BLOCKER, "version-naming",
              f"Version directory '{version}' does not match the vN.N convention "
              f"(e.g. v1.0, v2.0.1). The version segment binds the URI, the "
              f"filenames, and the citations.")
        return
    if stem and f"-{version}-" not in f"{stem}-":
        m = re.search(r"-v(\d+(\.\d+)+)-", stem)
        if m and f"v{m.group(1)}" != version:
            f.add(BLOCKER, "version-naming",
                  f"Delivery filename '{stem}' embeds version v{m.group(1)} but the "
                  f"package publishes under /{version}/: the files were renamed "
                  f"from a different version's package.")
        else:
            f.add(WARN, "version-naming",
                  f"Delivery filename '{stem}' does not embed the version segment "
                  f"'-{version}-' (Naming Directives shape: <base>-{version}-<stage>).")


def check_revision_collision(base: str, version: str, stage: str,
                             f: Findings) -> None:
    """A new submission's stage must not already exist on the live site: the
    revision increments instead (a 'CSD01' that has been live since 2024 is
    the next package's csd02 (the KMIP v3.0 scar, Jul 2026). Network-derived
    and advisory: WARN on collision, INFO listing the version's published
    stages, silent skip offline (set PUB_CHECK_OFFLINE=1 to force-skip)."""
    if os.getenv("PUB_CHECK_OFFLINE", "").lower() in {"1", "true", "yes"}:
        return
    if not base or not base.startswith(SITE + "/"):
        return
    import urllib.error
    import urllib.request

    def fetch(url: str) -> tuple[int, str]:
        req = urllib.request.Request(url, headers={"User-Agent": "pub-check"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, r.read(65536).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    status, _ = fetch(base)
    f.observe("revision-collision", this_stage_url=base, http_status=status or "(unreachable)")
    if status == 200:
        f.add(WARN, "revision-collision",
              f"Stage /{stage}/ is already published at {base}: a NEW submission "
              f"for {version} must use the next revision number instead. Ignore "
              f"this warning if you are re-checking the published package itself.")
    version_url = base.split(f"/{stage}/", 1)[0] + "/"
    status, listing = fetch(version_url)
    if status == 200 and listing:
        stages = sorted(set(re.findall(
            r'href="((?:wd|csd|cs|cnd|cn|os|ps|psd|pn|pnd|errata)\d*)/"', listing)))
        if stages:
            f.add(INFO, "revision-collision",
                  f"Published stages already live under {version_url}: "
                  f"{', '.join(stages)}.")



def check_odt(path: str, rel: str, f: Findings) -> None:
    """ODT source integrity, per .odt file anywhere in the package (a
    multi-part Work Product carries one per part). The OpenDocument
    container is a ZIP archive with a declared mimetype and an XML body;
    these are the mechanical facts about the authoritative source itself.
    Active content (embedded macros) is refused under the same policy the
    image checks apply to SVG scripts. Render fidelity against the TC's
    own precedent stays with the human audit."""
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        z = zipfile.ZipFile(path)
        names = z.namelist()
    except Exception as exc:
        f.add(BLOCKER, "odt-integrity",
              f"{rel}: ODT source does not open as a ZIP archive ({exc}): "
              f"the file is corrupt or not an OpenDocument package.")
        return ""
    mt = ""
    if "mimetype" not in names:
        f.add(BLOCKER, "odt-integrity",
              f"{rel}: ODT archive has no mimetype member; not a valid OpenDocument package.")
    else:
        mt = z.read("mimetype").decode("ascii", "replace").strip()
        if not mt.startswith("application/vnd.oasis.opendocument"):
            f.add(BLOCKER, "odt-integrity",
                  f"{rel}: ODT mimetype member declares '{mt}', which is not an OpenDocument type.")
    if "content.xml" not in names:
        f.add(BLOCKER, "odt-integrity",
              f"{rel}: ODT archive has no content.xml; the document body is missing.")
    else:
        try:
            ET.fromstring(z.read("content.xml"))
        except ET.ParseError as exc:
            f.add(BLOCKER, "odt-integrity",
                  f"{rel}: ODT content.xml does not parse as XML ({exc}).")
    macros = sorted({n.split("/")[0] for n in names
                     if n.startswith(("Basic/", "Scripts/"))})
    if macros:
        f.add(BLOCKER, "odt-integrity",
              f"{rel}: ODT archive carries embedded macro/script content "
              f"({', '.join(macros)}/): active content is refused on docs.oasis-open.org.")
    return mt



def check_filenames(items: dict[str, str], stage: str, f: Findings,
                    required: tuple[str, ...] = ("md", "html", "pdf")) -> str:
    """Delivery items must be <base>-<stage>.<ext>. Returns <base>-<stage>.
    `required` is the track's format set: (md, html, pdf) on the markdown
    track, (docx, html, pdf) on the DOCX-native track."""
    stems = {os.path.splitext(os.path.basename(p))[0] for p in items.values()}
    f.observe("filenames", stems=stems)
    if len(stems) > 1:
        f.add(BLOCKER, "filenames", f"Delivery items do not share one basename: {sorted(stems)}")
    stem = sorted(stems)[0] if stems else ""
    for bad in ("draft", "tmp", "rc"):
        if re.search(rf"[-_.]{bad}\d*$", stem) or f"-{bad}-" in stem:
            f.add(BLOCKER, "filenames",
                  f"Delivery filename '{stem}' carries a working token ('{bad}'); files must be "
                  f"named for the stage being published (…-{stage}.md/.html/.pdf).")
    if stem and not stem.endswith(f"-{stage}"):
        f.add(BLOCKER, "filenames",
              f"Delivery filename '{stem}' does not end in '-{stage}' (the stage directory name).")
    missing = set(required) - set(items)
    if missing:
        f.add(BLOCKER, "filenames", f"Missing delivery format(s): {', '.join(sorted(missing))}")
    return stem


def uri_path(u: str) -> str:
    """The path portion of a docs URL, ready for character inspection:
    scheme+host removed, query and fragment dropped, percent-decoded so an
    encoded %5F reads as the underscore it is. Used by the URI-character
    checks; a bare string with no scheme is returned unchanged."""
    p = u.split("://", 1)[-1]
    p = p.split("/", 1)[1] if "/" in p else ""
    p = p.split("?", 1)[0].split("#", 1)[0]
    return urllib.parse.unquote(p)


def check_front_matter(md_text: str, items: dict[str, str], version: str, stage: str,
                       f: Findings) -> str:
    """Validate This/Latest stage URL blocks. Returns the This-Stage base URL."""
    this_urls = stage_urls_from_md(md_text, "This")
    latest_urls = stage_urls_from_md(md_text, "Latest")
    f.observe("front-matter", this_stage_urls=this_urls or "(none)",
              latest_stage_urls=latest_urls or "(none)")
    # AC-NAMING-08: no underscore in a document (cover-page) URI. The
    # This/Latest-stage blocks are the URIs the current submission constructs
    # and controls; the Previous-stage block cites an immutable prior artifact
    # (Resource Permanence) the TC cannot rename, so it is out of scope here.
    f.observe("uri-chars", cover_uris_scanned=len(this_urls + latest_urls))
    for u in this_urls + latest_urls:
        if "_" in uri_path(u):
            f.add(BLOCKER, "uri-chars",
                  f"Underscore in a document (cover-page) URI: {u.rstrip('.,)')}. "
                  f"Naming Directives v1.7 s3 bars '_' from any filename or "
                  f"directory name used in a document URI (alphanumerics, "
                  f"'-' and '.' only).")
    base = ""
    if not this_urls:
        f.add(BLOCKER, "front-matter", "No 'This stage' URL block found in the markdown.")
    delivery_names = {os.path.basename(p) for p in items.values()}
    seen_ext = set()
    for u in this_urls + latest_urls:
        if not u.startswith(SITE + "/"):
            f.add(BLOCKER, "front-matter",
                  f"Stage URL is not under {SITE}: {u}")
    for u in this_urls:
        if f"/{version}/" not in u or f"/{stage}/" not in u:
            f.add(BLOCKER, "front-matter",
                  f"This-stage URL does not contain /{version}/ and /{stage}/: {u}")
        name = u.rstrip(".").rsplit("/", 1)[-1]
        if name not in delivery_names:
            f.add(BLOCKER, "front-matter",
                  f"This-stage URL points at '{name}' which is not a file in the package: {u}")
        else:
            seen_ext.add(os.path.splitext(name)[1].lstrip("."))
            base = u.rsplit("/", 1)[0] + "/"
    for ext in ("md", "html", "pdf"):
        if this_urls and ext not in seen_ext:
            f.add(WARN, "front-matter", f"This-stage block does not list the .{ext} artifact.")
    for u in latest_urls:
        if f"/{stage}/" in u:
            f.add(BLOCKER, "front-matter",
                  f"Latest-stage URL must point at the version root (no /{stage}/): {u}")
        if f"/{version}/" not in u:
            f.add(BLOCKER, "front-matter", f"Latest-stage URL not under /{version}/: {u}")
    # any other docs URL declaring a different version is a stale-draft tell,
    # except legitimate citations in the Previous-Stage / Related-Work blocks
    legit = set(stage_urls_from_md(md_text, "Previous"))
    rw = re.search(r"^#+ Related [Ww]ork.*?$(.*?)^#+ ", md_text, re.M | re.S)
    if rw:
        legit |= set(re.findall(r"https?://\S+?(?=[)\s\\]|$)", rw.group(1)))
    for u in set(re.findall(r"https?://docs\.oasis-open\.org/\S+", md_text)) - legit:
        m = re.search(r"/v(\d+\.\d+)/", u)
        if m and f"v{m.group(1)}" != version and "/templates/" not in u:
            f.add(WARN, "front-matter",
                  f"URL declares version v{m.group(1)} (package is {version}): {u.rstrip('.,)')}"
                  " -- confirm this is an intentional external reference.")
    return base


# OASIS member-only (Kavi) tool URIs: password-protected, must never be cited
# in a public work product (Naming Directives v1.7 s6.6). The two path shapes
# below are the unambiguous Kavi member-only tools; public docs.oasis-open.org
# and groups.oasis-open.org discussion links are NOT matched.
KAVI_MEMBER_URI = re.compile(
    r"https?://(?:www\.)?oasis-open\.org/(?:apps/org/|committees/download\.php)",
    re.IGNORECASE)


def check_member_uri(md_text: str, html_text: str, f: Findings) -> None:
    """AC-PACKAGING-18: no OASIS member-only (Kavi) URI cited in the package.
    Scans the authoritative markdown and the rendered HTML (code blocks
    included: a member-only link is a defect wherever it appears)."""
    hits = sorted({m.group(0) for t in (md_text, html_text)
                   for m in KAVI_MEMBER_URI.finditer(t)})
    f.observe("member-uri", member_only_uris=hits or "(none)")
    for u in hits:
        f.add(BLOCKER, "member-uri",
              f"Cites an OASIS member-only (Kavi) URI: {u}. Naming Directives "
              f"v1.7 s6.6 bars password-protected member-only references from "
              f"any TC document that is or may become public.")


def check_residue(md_text: str, html_text: str, f: Findings) -> None:
    f.observe("residue", scanned=[k for k, t in (("markdown", md_text), ("html", html_text)) if t])
    for label, text in (("markdown", strip_code_blocks(md_text, "md")),
                        ("html", strip_code_blocks(html_text, "html"))):
        for m in re.finditer(r"TODO\([^)]*\)|TODO:", text):
            f.add(BLOCKER, "residue", f"Editor TODO left in {label}: '{m.group(0)}'")
        for m in re.finditer(r"(?i)^\s*tbd\.?\s*$", text, re.M):
            f.add(BLOCKER, "residue", f"'tbd' placeholder section left in {label}.")
        if re.search(r"[Ww]ill be filled in", text):
            f.add(WARN, "residue",
                  f"'Will be filled in …' placeholder present in {label} (acceptable for an "
                  f"early stage; must be resolved before CS).")
        # Template instruction text that the editor was told to delete. The OASIS
        # Board-approved templates carry blocks of guidance for the editor and say
        # so explicitly: "All template instructions are included within angle
        # brackets and need to be deleted prior to publication." When one survives
        # it ships as if it were part of the specification. Scarred 21-Jul-2026:
        # KMIP Usage Guide v3.0 cnd01 s1.1 went to public review carrying "NOTE
        # (remove this note and following examples before publication)", and an
        # external reviewer found it on day 5 of the review.
        # Deliberately anchored on the imperative + "publication" so that ordinary
        # prose about the publication process cannot trip it.
        #
        # Scanned against TAG-STRIPPED, WHITESPACE-COLLAPSED prose, not the raw
        # text the checks above use. Word-generated HTML (the DOCX-native track)
        # hard-wraps mid-sentence and splits phrases across <span> runs, so the
        # KMIP instruction above is literally stored as "...and following\n
        # examples before publication". A pattern written against raw text misses
        # it, which is precisely how it reached public review.
        prose = re.sub(r"<[^>]+>", " ", text) if label == "html" else text
        prose = re.sub(r"\s+", " ", html_lib.unescape(prose))
        for m in re.finditer(
                r"(?i)\b(?:remove|delete|deleted|removed|strip)\b[^.;:]{0,80}?"
                r"\b(?:before|prior to)\s+publication\b", prose):
            f.add(BLOCKER, "residue",
                  f"Template instruction left in {label}: '{' '.join(m.group(0).split())}'. "
                  f"The OASIS work product templates mark editor guidance for deletion "
                  f"before publication; this block was not removed.")


def check_html(html_text: str, stem: str, f: Findings,
               anchor_severity: str = BLOCKER) -> None:
    """`anchor_severity` is BLOCKER on the markdown track (the author controls
    the source and must fix it) and WARN on the DOCX-native track (danglers
    there are source-DOCX artifacts: navigation-only, fix path is the TC's
    next revision, not the render)."""
    p = _AnchorParser()
    p.feed(html_text)
    title = " ".join(p.title.split())
    f.observe("html-title", title=title or "(absent)")
    f.observe("html-anchors",
              internal_links=len(set(p.internal_hrefs)), anchors=len(p.ids),
              unresolved=len({h for h in p.internal_hrefs if h not in p.ids}))
    f.observe("html-residue",
              title_block_headers=len(re.findall(r'<header\s+id="title-block-header"', html_text, re.I)),
              runner_paths=len(set(re.findall(r'(?:href|src)="(/home/runner/[^"]*)"', html_text))))
    if re.search(r"(?i)[\s\-–—](tmp|draft|wip)$", title):
        f.add(BLOCKER, "html-title", f"HTML <title> carries working residue: '{title}'")
    if title and stem.split("-")[0].replace("_", " ") and len(title) < 8:
        f.add(WARN, "html-title", f"HTML <title> looks too short: '{title}'")
    # Absorbed from publisher-toolkit lint_html.py (the render-time D-series):
    # D2 pandoc title-block residue and D3 CI runner-path leaks arrive at
    # intake too, because TC repos run the same shared workflows.
    if re.search(r'<header\s+id="title-block-header"', html_text, re.I):
        f.add(BLOCKER, "html-residue",
              "Stale pandoc <header id=\"title-block-header\"> block: renders the "
              "title twice on the PDF cover (lint D2).")
    for m in sorted(set(re.findall(r'(?:href|src)="(/home/runner/[^"]*)"', html_text))):
        f.add(BLOCKER, "html-residue",
              f"CI runner path leaked into the HTML: {m} (lint D3).")
    if title:
        flat = re.sub(r"\s+", " ", html_text)
        h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", flat, re.I | re.S)
        norm = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip().lower()
        dup = sum(1 for h in h1s if norm(h) == title.lower())
        if dup > 1:
            f.add(BLOCKER, "html-residue",
                  f"Document title appears in {dup} <h1> elements; the PDF cover "
                  f"renders the title twice (lint D1).")
    missing = sorted({h for h in p.internal_hrefs if h not in p.ids})
    for h in missing[:20]:
        hint = (" (stale Word TOC field: the bookmark is absent from the source DOCX; "
                "regenerate the TOC in Word)") if h.startswith("_Toc") else ""
        f.add(anchor_severity, "html-anchors",
              f"Internal link '#{h}' has no matching anchor in the HTML.{hint}")
    if len(missing) > 20:
        f.add(anchor_severity, "html-anchors",
              f"...and {len(missing) - 20} more unresolved internal links.")
    if missing:
        f.add(INFO, "html-anchors",
              f"{len(missing)} of {len(set(p.internal_hrefs))} internal links unresolved.")
    if not p.internal_hrefs:
        f.add(WARN, "html-anchors", "HTML contains no internal (fragment) links at all; "
                                    "expected a linked Table of Contents.")


def check_md_links(md_text: str, f: Findings) -> None:
    md_text = strip_code_blocks(md_text, "md")
    f.observe("md-links", links_scanned=len(re.findall(r"\[<?\S+?>?\]\(\S+?\)", md_text)))
    for m in re.finditer(r"\[<?(\S+?)>?\]\((\S+?)\)", md_text):
        if m.group(1) == m.group(2) and m.group(1).startswith("http"):
            f.add(WARN, "md-links",
                  f"Dual link [url](url); prefer a bare URL (autolinked) or real anchor text: "
                  f"{m.group(2)}")
    for i, line in enumerate(md_text.splitlines(), 1):
        if re.search(r"https?://\S+\.\\$", line):
            f.add(BLOCKER, "md-links",
                  f"Line {i}: bare URL runs into '.\\' with no space; pandoc autolink pulls the "
                  f"period and backslash into the href and eats the line break. Use '. \\'.")


def check_md_fences(md_text: str, f: Findings) -> None:
    """Absorbed from publisher-toolkit preprocess_md.py (lint D6): an opening
    code fence whose info string carries trailing text (``` yaml <!-- note -->)
    is not recognized as a fence by pandoc's classic fenced_code_blocks -- the
    whole block collapses to inline code and loses its formatting. Shipped
    once (DPS prov-meta, 28 yaml blocks, May 2026; editor-flagged blocker).
    The curly-attribute form (```{.lang title="x"}) is fine."""
    in_fence = False
    delim = ""
    f.observe("fence-collapse", fences_scanned=len(re.findall(r"^\s{0,3}(?:`{3,}|~{3,})", md_text, re.M)))
    for i, line in enumerate(md_text.splitlines(), 1):
        m = re.match(r"^(\s{0,3})(`{3,}|~{3,})(.*)$", line)
        if not m:
            continue
        marker, info = m.group(2), m.group(3).strip()
        if in_fence:
            if marker[0] == delim and not info:
                in_fence = False
            continue
        in_fence = True
        delim = marker[0]
        if info and not info.startswith("{") and re.match(r"^[\w+-]+\s+\S", info):
            f.add(BLOCKER, "fence-collapse",
                  f"Line {i}: opening fence info string carries trailing text "
                  f"('{info[:40]}...'): pandoc does not recognize it as a fence and "
                  f"the block collapses to inline code. Use ```{{.lang title=\"...\"}} "
                  f"or drop the trailing text.")


IMG_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


def check_image_policy(stage_dir: str, html_text: str, f: Findings) -> None:
    """Absorbed from publisher-toolkit inline_images.py (lint D7). Two halves:
    HTML constructs the publication pipeline refuses (empty/absolute/traversal
    src, srcset, <picture>), and image-file safety -- an SVG carrying <script>,
    event handlers, or external refs is active content on docs.oasis-open.org.
    Size caps mirror the inliner's policy (warn 500KB, refuse 2MB, 5MB total)."""
    flat = (html_text or "").replace("\r", "").replace("\n", "")
    f.observe("image-policy", img_tags=len(re.findall(r'<img\b', flat, re.I)))
    for m in re.finditer(r'<img\b[^>]*>', flat, re.I):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]*)"', tag)
        src = src_m.group(1).strip() if src_m else ""
        if src_m and not src:
            f.add(BLOCKER, "image-policy", "Empty <img src> in the HTML.")
        elif src.startswith("/") and not src.startswith("//"):
            f.add(BLOCKER, "image-policy",
                  f"Absolute-path <img src=\"{src[:60]}\">: resolves outside the "
                  f"package on publication.")
        elif ".." in src.split("?")[0].split("/"):
            f.add(BLOCKER, "image-policy",
                  f"Path-traversal <img src=\"{src[:60]}\">: escapes the package.")
        if "srcset=" in tag.lower():
            f.add(WARN, "image-policy",
                  "<img srcset> present: the publication pipeline refuses "
                  "responsive-image constructs (self-containment policy).")
    if re.search(r"<picture\b", flat, re.I):
        f.add(WARN, "image-policy",
              "<picture> element present: the publication pipeline refuses it "
              "(self-containment policy).")
    total = 0
    for root, _dirs, files in os.walk(stage_dir):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in IMG_EXTS:
                continue
            p = os.path.join(root, name)
            rel = os.path.relpath(p, stage_dir)
            size = os.path.getsize(p)
            total += size
            if size > 2_097_152:
                f.add(WARN, "image-policy",
                      f"{rel}: {size // 1024}KB exceeds the pipeline's 2MB "
                      f"per-image refusal cap.")
            if ext == ".svg":
                try:
                    body = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if re.search(r"<script\b", body, re.I):
                    f.add(BLOCKER, "image-policy",
                          f"{rel}: SVG contains <script> -- active content is "
                          f"refused on docs.oasis-open.org.")
                if re.search(r"\son\w+\s*=", body, re.I):
                    f.add(BLOCKER, "image-policy",
                          f"{rel}: SVG carries inline event handlers (on*=) -- "
                          f"active content is refused.")
                if re.search(r"<(image|use)\b[^>]*href=\"https?://", body, re.I):
                    f.add(BLOCKER, "image-policy",
                          f"{rel}: SVG references an external image/use target; "
                          f"the published artifact would not be self-contained.")
    f.observe("image-policy", image_payload_bytes=total)
    if total > 5_242_880:
        f.add(WARN, "image-policy",
              f"Cumulative image payload {total // 1_048_576}MB exceeds the "
              f"pipeline's 5MB inlining cap.")


def check_pdf_cover(pdf_path: str, title: str, f: Findings) -> None:
    """Absorbed from publisher-toolkit step_2_convert_html_to_pdf.py: A1 (the
    document title must appear exactly once on the PDF cover page -- twice
    means stale pandoc header residue baked into the render; shipped on DPS
    May 2026) and A2 (no /home/runner CI path anywhere in the PDF text)."""
    pdftotext = shutil.which("pdftotext")
    if not pdftotext or not title or title == "-":
        return
    try:
        page1 = subprocess.run([pdftotext, "-l", "1", pdf_path, "-"],
                               capture_output=True, text=True, timeout=60).stdout
        full = subprocess.run([pdftotext, pdf_path, "-"],
                              capture_output=True, text=True, timeout=120).stdout
    except Exception:  # noqa: BLE001 - pdf-sync already reports readability
        return
    norm = re.sub(r"\s+", " ", title.lower())
    count = re.sub(r"\s+", " ", page1.lower()).count(norm)
    f.observe("pdf-cover", title=title, cover_page_occurrences=count,
              runner_path_in_pdf="/home/runner/" in full)
    if count > 1:
        f.add(BLOCKER, "pdf-cover",
              f"Document title appears {count} times on the PDF cover page "
              f"(stale title-block residue baked into the render).")
    if "/home/runner/" in full:
        f.add(BLOCKER, "pdf-cover",
              "CI runner path (/home/runner/) leaked into the rendered PDF text.")


def check_schemas(stage_dir: str, base_this_stage: str, version: str, stage: str,
                  f: Findings) -> None:
    if not base_this_stage:
        return
    # $id convention: schemas identify at the version root (latest), not the stage path
    latest_root = base_this_stage.replace(f"/{stage}/", "/")
    _json_files = [n for r, _d, fs in os.walk(stage_dir) for n in fs if n.endswith(".json")]
    f.observe("schema-id", json_files=len(_json_files), expected_id_root=latest_root)
    for root, _dirs, files in os.walk(stage_dir):
        for name in files:
            if not name.endswith(".json"):
                continue
            path = os.path.join(root, name)
            try:
                doc = json.loads(read_text(path))
            except json.JSONDecodeError as e:
                f.add(BLOCKER, "schema-id", f"{name}: not valid JSON ({e})")
                continue
            if not isinstance(doc, dict) or "$id" not in doc:
                continue
            rel = os.path.relpath(path, stage_dir)
            expected = latest_root + rel.replace(os.sep, "/")
            declared = doc["$id"]
            if declared != expected:
                roots = {latest_root, re.sub(r"errata\d+/$", "", latest_root)}
                same_root = any(declared.startswith(r) for r in roots)
                same_name = declared.rsplit("/", 1)[-1] == name
                if same_root and same_name:
                    f.add(WARN, "schema-id",
                          f"{rel}: $id is '{declared}', a flattened path under the version "
                          f"root (CSAF v2.0 publishes this way). Confirm a copy publishes "
                          f"at the $id location, or align $id with '{expected}'.")
                else:
                    f.add(BLOCKER, "schema-id",
                          f"{rel}: $id is '{declared}' but the file publishes under "
                          f"'{latest_root}'. An implementer following the $id gets a 404 "
                          f"or the wrong document.")
            # any self-referencing const inside the schema must agree with $id
            blob = json.dumps(doc)
            for u in set(re.findall(r"https://docs\.oasis-open\.org/[^\"\s]+\.json", blob)):
                if u.rsplit("/", 1)[-1] == name and u != declared and u != expected:
                    f.add(BLOCKER, "schema-id",
                          f"{rel}: internal reference '{u}' disagrees with $id '{declared}'.")


def check_pdf(pdf_path: str, this_urls_base: str, version: str, f: Findings) -> None:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        f.add(WARN, "pdf-sync", "pdftotext not on PATH: the PDF front-matter cross-check was "
                                "SKIPPED. The intake side will run it; install poppler to run "
                                "it here.")
        return
    try:
        proc = subprocess.run([pdftotext, "-l", "3", pdf_path, "-"],
                              capture_output=True, text=True, timeout=60)
    except Exception as e:  # noqa: BLE001 - report, do not crash the gate
        f.add(WARN, "pdf-sync", f"pdftotext failed: {e}")
        return
    if proc.returncode != 0:
        f.add(BLOCKER, "pdf-sync",
              f"pdftotext could not read the PDF (exit {proc.returncode}): "
              f"{proc.stderr.strip()[:200]}")
        return
    txt = proc.stdout
    f.observe("pdf-sync", pdftotext="present",
              this_stage_base_in_pdf=bool(this_urls_base) and this_urls_base in txt.replace("\n", ""))
    if this_urls_base and this_urls_base not in txt.replace("\n", ""):
        f.add(BLOCKER, "pdf-sync",
              f"PDF front matter does not contain the canonical this-stage base URL "
              f"({this_urls_base}); the PDF was likely rendered from an older draft.")
    # a different version of THIS spec in the PDF is suspicious (previous-stage
    # citations are expected, so this stays a warning)
    spec_base = ""
    if this_urls_base:
        spec_base = this_urls_base.split(f"/{version}/", 1)[0]
    if spec_base:
        for m in set(re.findall(re.escape(spec_base) + r"/v(\d+\.\d+)/", txt)):
            if f"v{m}" != version:
                f.add(WARN, "pdf-sync",
                      f"PDF cites {spec_base}/v{m}/ (package is {version}); expected only "
                      f"as a previous-stage reference -- confirm.")


# Template front-matter sections, in canonical order. (label, pattern, required)
TEMPLATE_SECTIONS = [
    ("This stage/version", r"This (Stage|Version)", True),
    ("Previous stage/version", r"Previous (Stage|Version)", True),
    ("Latest stage/version", r"Latest (Stage|Version)", True),
    ("Technical Committee", r"Technical Committee", True),
    ("Chair(s)", r"Chairs?\b", True),
    ("Editor(s)", r"Editors?\b", True),
    ("Abstract", r"Abstract", True),
    ("Status", r"(Document )?Status", False),
    ("Citation format", r"Citation", False),
    ("Notices", r"Notices|License, Document Status", False),
]


def check_template(md_text: str, html_text: str, f: Findings) -> None:
    """Template structure per the OASIS spec template and TC Process:
    front-matter section order, mandatory Conformance section, stylesheet."""
    positions = []
    for label, pat, required in TEMPLATE_SECTIONS:
        m = re.search(rf"^#+\s+{pat}", md_text, re.M | re.I)
        if not m:
            if required:
                f.add(BLOCKER, "template",
                      f"Required front-matter section missing: {label}.")
        else:
            positions.append((m.start(), label))
    f.observe("template", sections_found=[lbl for _pos, lbl in sorted(positions)],
              conformance_section=bool(re.search(r"^#+\s+[\d.\sA-Za-z]*Conformance", md_text, re.M | re.I)))
    if positions != sorted(positions):
        order = " -> ".join(lbl for _pos, lbl in positions)
        f.add(WARN, "template",
              f"Front-matter sections out of template order: {order}.")

    # TC Process: every Standards Track Work Product carries a Conformance section
    if not re.search(r"^#+\s+[\d.\sA-Za-z]*Conformance", md_text, re.M | re.I):
        f.add(BLOCKER, "template",
              "No Conformance section found. The TC Process requires a conformance "
              "clauses section in every Standards Track Work Product.")

    # Stylesheet adherence: the HTML should carry the OASIS look. Canonical is the
    # markdown-styles CSS from docs.oasis-open.org (linked or localized); a spec
    # shipping its own CSS is accepted practice but must be a conscious choice.
    if html_text:
        links = re.findall(r"<link[^>]+rel=[\"']?stylesheet[\"']?[^>]*>", html_text, re.I)
        hrefs = " ".join(links)
        inline_css = re.findall(r"<style\b", html_text, re.I)
        f.observe("template-css",
                  stylesheet_links=len(links), inline_style_blocks=len(inline_css))
        if re.search(r"markdown-styles[^\"']*\.css", hrefs):
            pass  # canonical stylesheet
        elif links or inline_css:
            body_font = ""
            m = re.search(r"font-family\s*:\s*([^;}}]+)", html_text, re.I)
            if m:
                body_font = m.group(1).strip()
            if body_font and not re.search(r"(?i)liberation|arial|helvetica", body_font):
                f.add(WARN, "template-css",
                      f"HTML does not use the canonical OASIS stylesheet and its primary "
                      f"font-family is '{body_font}'; the template look is Liberation "
                      f"Sans / Arial. Confirm the deviation is intentional.")
            else:
                f.add(INFO, "template-css",
                      "HTML ships its own stylesheet rather than the canonical "
                      "markdown-styles CSS; fonts match the template family. Accepted "
                      "practice (OpenEoX publishes this way), noting it for the record.")
        else:
            f.add(BLOCKER, "template-css",
                  "HTML carries no stylesheet at all (no <link rel=stylesheet>, no "
                  "<style> block).")


def check_correction_classes(md_text: str, stage_dir: str, base: str, stage: str,
                             f: Findings) -> None:
    """Defect classes from historical publication correction rounds
    (prov-meta May 2026, DMLex Jun 2026, UBL Aug 2025)."""
    prose = strip_code_blocks(md_text, "md")

    # DMLex class: files the spec cites under its own stage path must ship
    if base:
        for u in set(re.findall(re.escape(base) + r"[\w./%-]+", prose)):
            rel = u[len(base):].rstrip(".,)\\")
            if rel and not rel.endswith((".md", ".html", ".pdf")):
                if not os.path.isfile(os.path.join(stage_dir, rel)):
                    f.add(BLOCKER, "package-refs",
                          f"The document cites {u} under its own stage path, but "
                          f"'{rel}' is not in the package: it will 404 on publication.")

    # prov-meta class: visible URL and link target disagree (rename artifacts)
    for m in re.finditer(r"\[(https?://[^\]\s]+)\]\((https?://[^)\s]+)\)", prose):
        shown, target = m.group(1).rstrip("/"), m.group(2).rstrip("/")
        if shown != target:
            f.add(BLOCKER, "link-mismatch",
                  f"Visible URL and link target disagree: text shows '{m.group(1)}' but "
                  f"links to '{m.group(2)}'. One of them is wrong.")

    # prov-meta class: double slash in a relative path (Cloudflare 404s it)
    for m in set(re.findall(r"\]\((\.?/[^)\s]*//[^)\s]*)\)", prose)):
        f.add(BLOCKER, "double-slash",
              f"Relative path contains a double slash: '{m}'. Browsers tolerate it; the "
              f"CDN returns 404.")

    # prov-meta class: horizontal rule between logo and title becomes a PDF
    # page break in the publication CSS (blank first page)
    head = md_text[:600]
    f.observe("cover-hr", rule_after_logo=bool(
        re.search(r"OASISLogo[^\n]*\)\s*\n+\s*(-{3,}|\*{3,}|_{3,})\s*\n", head)))
    f.observe("package-refs", own_stage_citations_checked=len(set(
        re.findall(re.escape(base) + r"[\w./%-]+", prose))) if base else 0)
    f.observe("link-mismatch", shown_target_pairs=len(re.findall(
        r"\[(https?://[^\]\s]+)\]\((https?://[^)\s]+)\)", prose)))
    f.observe("double-slash", double_slash_paths=len(set(
        re.findall(r"\]\((\.?/[^)\s]*//[^)\s]*)\)", prose))))
    if re.search(r"OASISLogo[^\n]*\)\s*\n+\s*(-{3,}|\*{3,}|_{3,})\s*\n", head):
        f.add(WARN, "cover-hr",
              "Horizontal rule between the OASIS logo and the title: the publication "
              "CSS treats <hr/> as a page break, which opens the PDF with a blank page. "
              "Harmless in other renderers; remove if publishing through the OASIS "
              "HTML-to-PDF path.")

    # prov-meta class: a 'Latest'-labelled URL for THIS spec carrying the
    # stage segment (must be the persistent version-root path)
    spec_base = base.split(f"/{stage}/", 1)[0] + "/" if base and f"/{stage}/" in base else ""
    if spec_base:
        for line in prose.splitlines():
            if not re.match(r"\s*(?:[*+-]\s*)?Latest[\w /]*:", line, re.I):
                continue
            for u in re.findall(r"https?://docs\.oasis-open\.org/\S+", line):
                if u.startswith(spec_base) and f"/{stage}/" in u:
                    f.add(BLOCKER, "front-matter",
                          f"'Latest'-labelled URL carries the stage segment /{stage}/ "
                          f"(should be the persistent version-root path): {u.rstrip('.,)')}")


def check_pdf_fonts(stage_dir: str, pdf_path: str, html_text: str, f: Findings) -> None:
    """The PDF's embedded fonts should match the font families the package's own
    CSS declares (the CSS is the typography authority for a publication).
    Divergence is a finding, not a blocker: render class is judged against the
    TC's precedent. Soft-degrades when poppler's pdffonts is absent, and skips
    when the package declares no font authority of its own."""
    declared_src = html_text or ""
    for root, _dirs, files in os.walk(stage_dir):
        for name in files:
            if name.endswith(".css"):
                declared_src += read_text(os.path.join(root, name))
    families = set()
    for decl in re.findall(r"font-family\s*:\s*([^;}}\n\"]+)", declared_src, re.I):
        for fam in decl.split(","):
            fam = fam.strip().strip("'\"").lower()
            if fam and fam not in {"serif", "sans-serif", "monospace", "cursive",
                                   "fantasy", "system-ui", "inherit"}:
                families.add(re.sub(r"[\s_-]", "", fam))
    if not families:
        f.add(INFO, "pdf-fonts", "Package declares no local font authority (no "
                                 "font-family in its HTML/CSS); font check skipped.")
        return
    pdffonts = shutil.which("pdffonts")
    if not pdffonts:
        f.add(INFO, "pdf-fonts", "pdffonts (poppler) not on PATH; embedded-font "
                                 "check skipped. The intake side runs it.")
        return
    try:
        proc = subprocess.run([pdffonts, pdf_path], capture_output=True, text=True,
                              timeout=60)
    except Exception as e:  # noqa: BLE001
        f.add(WARN, "pdf-fonts", f"pdffonts failed: {e}")
        return
    embedded = set()
    for line in proc.stdout.splitlines()[2:]:
        name = line.split()[0] if line.split() else ""
        if not name or name == "[none]":
            continue
        name = re.sub(r"^[A-Z]{6}\+", "", name)
        base = re.split(r"[-,]", name)[0]
        if base:
            embedded.add(base)
    f.observe("pdf-fonts", css_declared_families=families, pdf_embedded_fonts=embedded)
    stray = sorted(b for b in embedded
                   if not any(fam in b.lower().replace(" ", "") or
                              b.lower().replace(" ", "") in fam for fam in families))
    if stray:
        f.add(WARN, "pdf-fonts",
              f"PDF embeds fonts not declared by the package's own CSS: "
              f"{', '.join(stray)}. The CSS declares: {', '.join(sorted(families))}. "
              f"Confirm the divergence is intentional (pdffonts <file.pdf> re-checks "
              f"this after a toolchain change).")


def check_manifest(stage_dir: str, f: Findings) -> None:
    mpath = os.path.join(stage_dir, "manifest.json")
    f.observe("manifest", manifest_json="present" if os.path.exists(mpath) else "absent")
    if not os.path.exists(mpath):
        f.add(INFO, "manifest", "No manifest.json in the package. Emit one (--emit-manifest or "
                                "your own tool) and intake verification becomes automatic.")
        return
    try:
        man = json.loads(read_text(mpath))
    except json.JSONDecodeError as e:
        f.add(BLOCKER, "manifest", f"manifest.json is not valid JSON: {e}")
        return
    if man.get("schema") == "nide-manifest":
        # A nide build-provenance record (schema nide-manifest, currently v1.0):
        # source files, build outputs, and toolchain, hashed at build time in the
        # TC repository. Its output paths name the build tree, not the delivery
        # package, so per-item path verification does not apply. Binary-norm
        # hashes (the PDFs) survive the delivery renaming byte-identical, so
        # those are matched against the package's own files.
        tool = (man.get("toolchain") or {}).get("nide", "?")
        rev = str((man.get("source") or {}).get("revision") or "")[:12]
        f.observe("manifest", nide_manifest=f"nide {tool}" + (f" @ {rev}" if rev else ""))
        binary = {h.get("value") for o in (man.get("outputs") or {}).values()
                  for h in (o.get("hashes") or [])
                  if h.get("alg") == "sha256" and h.get("norm") == "binary"}
        pdfs = [os.path.relpath(os.path.join(r, n), stage_dir)
                for r, _d, files in os.walk(stage_dir) for n in files
                if n.lower().endswith(".pdf")]
        for rel in sorted(pdfs):
            digest = sha256_file(os.path.join(stage_dir, rel))
            if digest in binary:
                f.add(INFO, "manifest",
                      f"{rel} is byte-identical to a nide build output "
                      f"(sha256 {digest[:12]}…): the delivered PDF is the recorded build.")
            else:
                f.add(INFO, "manifest",
                      f"{rel} matches none of the manifest's binary-norm hashes: the "
                      f"delivered PDF is not the build this manifest records. Confirm "
                      f"the package and manifest come from the same build.")
        f.add(INFO, "manifest",
              "nide-manifest is a build-provenance record; per-item delivery "
              "verification (path + sha256 of each shipped file) still comes from "
              "the items[] manifest (--emit-manifest). Ship both until the formats "
              "converge.")
        return
    if not man.get("items"):
        f.add(INFO, "manifest",
              "manifest.json parses but lists no items[]; nothing was verified. "
              "Emit one with --emit-manifest, or ship a recognized provenance "
              "record (schema: nide-manifest).")
        return
    for item in man.get("items", []):
        p = os.path.join(stage_dir, item.get("path", ""))
        if not os.path.isfile(p):
            f.add(BLOCKER, "manifest", f"manifest lists missing file: {item.get('path')}")
            continue
        actual = sha256_file(p)
        if actual != item.get("sha256"):
            f.add(BLOCKER, "manifest",
                  f"sha256 mismatch for {item['path']}: manifest {item.get('sha256')}, "
                  f"file {actual}")


def emit_manifest(stage_dir: str, version: str, stage: str) -> str:
    items = []
    for root, _dirs, files in os.walk(stage_dir):
        for name in sorted(files):
            if name == "manifest.json" or name.endswith("-manifest.txt"):
                continue
            p = os.path.join(root, name)
            rel = os.path.relpath(p, stage_dir).replace(os.sep, "/")
            ext = os.path.splitext(name)[1].lstrip(".").lower()
            role = {"md": "authoritative", "html": "delivery", "pdf": "delivery",
                    "json": "schema"}.get(ext, "other")
            items.append({"path": rel, "role": role, "sha256": sha256_file(p),
                          "bytes": os.path.getsize(p)})
    commit = os.environ.get("GITHUB_SHA", "")
    if not commit:
        try:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                    text=True, cwd=stage_dir, timeout=10).stdout.strip()
        except Exception:  # noqa: BLE001
            commit = ""
    tools = {}
    for tool in ("pandoc", "typst", "tidy"):
        exe = shutil.which(tool)
        if exe:
            try:
                v = subprocess.run([exe, "--version"], capture_output=True, text=True,
                                   timeout=10).stdout.splitlines()[0]
                tools[tool] = v
            except Exception:  # noqa: BLE001
                pass
    man = {"version": version, "stage": stage, "source": {"commit": commit},
           "tools": tools, "items": items}
    out = os.path.join(stage_dir, "manifest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2)
        fh.write("\n")
    return out


def emit_manifest_txt(stage_dir: str, version: str, stage: str) -> str:
    """The Work Product Manifest File: the human-readable staff record
    published beside the release, reviving the practice OASIS Staff kept
    for years (see the OpenDocument releases for the precedent, e.g.
    /office/OpenDocument/v1.4/csd01/OpenDocument-v1.4-csd01-manifest.txt).
    Bibliographic block, ZIP archive listing, SHA-256 digests. Digests are
    for casual integrity checking, not security."""
    import datetime
    import zipfile

    items = find_delivery_items(stage_dir, ("md", "docx", "odt", "html", "pdf"))
    stem = ""
    for k in ("html", "pdf", "md", "docx", "odt"):
        if k in items:
            stem = os.path.splitext(os.path.basename(items[k]))[0]
            break
    name = (stem + "-manifest.txt") if stem else "manifest.txt"
    out = os.path.join(stage_dir, name)

    title = ""
    base_uri = ""
    if "html" in items:
        html = read_text(items["html"])
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
        m = re.search(r"https://docs\.oasis-open\.org/[^\s\"'<>]*?/"
                      + re.escape(stage) + "/", html)
        if m:
            base_uri = m.group(0)

    zips = sorted(n for n in os.listdir(stage_dir) if n.lower().endswith(".zip"))
    lines = [
        "Work Product Manifest File",
        "==========================",
        "",
        "This manifest is an administrative metadata record produced as part",
        "of the OASIS Work Product publication process. It lists the artifacts",
        "that constitute this release, with SHA-256 digests so a locally held",
        "file can be checked against the published one. The digests support",
        "casual integrity checking (disk corruption, silent alteration), not",
        "security. Generated by oasis_pub_check.py --emit-manifest",
        "(OASIS-Docs/publication-assurance); the machine-readable companion",
        "is manifest.json in this directory.",
        "",
        "====================================",
        "Essential bibliographic information",
        "====================================",
        "",
        f"Title:          {title or '(not stated in the package cover)'}",
        f"Version:        {version}",
        f"Approval stage: {stage}",
        f"Generated:      {datetime.date.today().isoformat()}",
    ]
    if base_uri:
        lines += [f"Release URI:    {base_uri}",
                  f"Manifest URI:   {base_uri}{name}"]
    for z in zips:
        lines += ["", "=====================", "ZIP archive contents",
                  "=====================", "", f"Archive: {z}", "",
                  f"{'Length':>10}  {'Date':>10}  {'CRC-32':>8}  Name",
                  f"{'-'*10}  {'-'*10}  {'-'*8}  {'-'*4}"]
        try:
            with zipfile.ZipFile(os.path.join(stage_dir, z)) as zf:
                total = n = 0
                for zi in zf.infolist():
                    d = "%04d-%02d-%02d" % zi.date_time[:3]
                    lines.append(f"{zi.file_size:>10}  {d}  "
                                 f"{zi.CRC:08x}  {zi.filename}")
                    total += zi.file_size
                    n += 1
                lines += [f"{'-'*10}{' '*24}{'-'*4}",
                          f"{total:>10}{' '*24}{n} files"]
        except Exception as exc:  # noqa: BLE001
            lines.append(f"(zip listing unavailable: {exc})")
    lines += ["", "=" * 68,
              "SHA-256 digest values for files in this release directory",
              "=" * 68, ""]
    for root, _dirs, files in os.walk(stage_dir):
        for fn in sorted(files):
            rel = os.path.relpath(os.path.join(root, fn),
                                  stage_dir).replace(os.sep, "/")
            if fn.endswith("-manifest.txt") or fn == "manifest.txt":
                continue
            lines.append(f"{sha256_file(os.path.join(root, fn))}  {rel}")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(chr(10).join(lines) + chr(10))
    return out

JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_DIRS = {"__MACOSX", ".git", ".venv", "venv", "node_modules"}


def check_hygiene(stage_dir: str, f: Findings, delivery_names: set | None = None) -> None:
    """OS junk and case problems. The publication origin is case-sensitive:
    a mixed-case filename means every lowercase citation of it 404s."""
    delivery_names = delivery_names or set()
    _all = [os.path.relpath(os.path.join(r, n), stage_dir)
            for r, _d, fs in os.walk(stage_dir) for n in fs]
    f.observe("junk-files", files_walked=len(_all))
    f.observe("case", mixed_case_files=[p for p in _all
              if os.path.basename(p) != os.path.basename(p).lower()
              and os.path.basename(p) != "OASISLogo-v3.0.png"] or "(none)")
    f.observe("symlinks", symlinks_found=sum(
        1 for r, ds, fs in os.walk(stage_dir) for n in ds + fs
        if os.path.islink(os.path.join(r, n))))
    for root, dirs, files in os.walk(stage_dir):
        # Self/parent-referential symlinks materialize into unbounded directory
        # recursion on deploy (rsync -L, s3 sync --follow-symlinks): KMIP
        # Profiles v3.0 csd01 shipped 41 nested levels (4,095 junk objects)
        # from a single 'kmip-v3.0 -> .' (found 15 Jul 2026).
        for name in list(dirs) + files:
            p = os.path.join(root, name)
            if os.path.islink(p):
                tgt = os.path.realpath(p)
                here = os.path.realpath(root)
                if tgt == here or here.startswith(tgt + os.sep):
                    rel = os.path.relpath(p, stage_dir)
                    f.add(BLOCKER, "symlinks",
                          f"Symlink '{rel}' points at its own ancestor "
                          f"('{os.readlink(p)}'): deploys materialize symlinks, so this "
                          f"expands into unbounded directory recursion on the CDN origin.")
        for d in list(dirs):
            if d in JUNK_DIRS:
                f.add(BLOCKER, "junk-files",
                      f"Working directory '{d}/' inside the package; remove before submitting.")
                dirs.remove(d)
        for name in files:
            if name in JUNK_NAMES or name.endswith(("~", ".bak", ".orig", ".swp")):
                f.add(BLOCKER, "junk-files",
                      f"Junk file in package: {os.path.relpath(os.path.join(root, name), stage_dir)}")
            elif name != name.lower() and name != "OASISLogo-v3.0.png":
                rel = os.path.relpath(os.path.join(root, name), stage_dir)
                sev = BLOCKER if name in delivery_names else WARN
                f.add(sev, "case",
                      f"Mixed-case filename '{rel}': the publication host is case-sensitive "
                      f"and canonical paths are lowercase; lowercase citations of this file "
                      f"will 404." + ("" if sev == BLOCKER else " (auxiliary file: warning; "
                      "published precedent exists, e.g. -DIFF.pdf)"))


def check_policy(md_text: str, html_text: str, version: str, stage: str,
                 f: Findings) -> None:
    """TC Handbook / template conventions that repeatedly bounce submissions."""
    prose = strip_code_blocks(md_text, "md")
    f.observe("dead-lists", md_lists_addresses=sorted(set(
        re.findall(r"[\w.+-]+@lists\.oasis-open\.org", prose))) or "(none)")
    f.observe("rfc-keywords",
              normative_keywords_present=bool(re.search(
                  r"\b(MUST NOT|MUST|SHALL NOT|SHALL|SHOULD NOT|SHOULD|MAY|REQUIRED|RECOMMENDED|OPTIONAL)\b", prose)),
              rfc2119_cited=bool(re.search(r"RFC\s?2119", md_text)),
              rfc8174_cited=bool(re.search(r"RFC\s?8174", md_text)))
    f.observe("logo", logo_sources=sorted(set(
        re.findall(r"!\[[^\]]*\]\((\S*?[Ll]ogo\S*?)\)", md_text))) or "(none)")
    f.observe("case", md_docs_urls_scanned=len(set(
        re.findall(r"https://docs\.oasis-open\.org/\S+", prose))))

    # dead mailing-list infrastructure: mail to lists.oasis-open.org silently fails
    for m in sorted(set(re.findall(r"[\w.+-]+@lists\.oasis-open\.org", prose))):
        f.add(BLOCKER, "dead-lists",
              f"References mailing address '{m}': lists.oasis-open.org no longer accepts "
              f"mail (messages fail silently). Point comments at the TC's Higher Logic "
              f"comment facility instead.")
    if "lists.oasis-open.org/archives" in prose:
        f.add(WARN, "dead-lists",
              "Links into lists.oasis-open.org/archives: verify each archive link still "
              "resolves; the list infrastructure is being retired.")

    # normative keywords demand the keyword references
    if re.search(r"\b(MUST NOT|MUST|SHALL NOT|SHALL|SHOULD NOT|SHOULD|MAY|"
                 r"REQUIRED|RECOMMENDED|OPTIONAL)\b", prose):
        if not re.search(r"RFC\s?2119", md_text):
            f.add(BLOCKER, "rfc-keywords",
                  "Document uses normative key words but does not cite RFC 2119 in its "
                  "references / key-words section.")
        elif not re.search(r"RFC\s?8174", md_text):
            f.add(WARN, "rfc-keywords",
                  "RFC 2119 is cited but RFC 8174 (uppercase-only clarification) is not; "
                  "the current template cites both.")

    # canonical logo
    for m in set(re.findall(r"!\[[^\]]*\]\((\S*?[Ll]ogo\S*?)\)", md_text)):
        if m != "https://docs.oasis-open.org/templates/OASISLogo-v3.0.png":
            f.add(WARN, "logo",
                  f"Logo source '{m}' is not the canonical "
                  f"https://docs.oasis-open.org/templates/OASISLogo-v3.0.png")

    # previous stage: anything past 01 must cite its predecessor
    m = re.fullmatch(r"([a-z]+)(\d\d)", stage)
    if m and int(m.group(2)) > 1:
        prev = stage_urls_from_md(md_text, "Previous")
        if not any("docs.oasis-open.org" in u for u in prev):
            f.add(BLOCKER, "previous-stage",
                  f"Stage {stage} must cite its previous stage URLs; the Previous-Stage "
                  f"block is empty or N/A.")

    # date agreement between md and html front matter, and copyright year
    md_date = re.search(r"^#+\s+(\d{1,2} \w+ \d{4})\s*$", md_text, re.M)
    _cr = re.search(r"Copyright\s+©?\s*OASIS Open\s+(\d{4})", md_text)
    f.observe("date-sync", document_date=md_date.group(1) if md_date else "(not found)",
              copyright_year=_cr.group(1) if _cr else "(not found)")
    if md_date:
        if html_text and md_date.group(1) not in html_text:
            f.add(BLOCKER, "date-sync",
                  f"Front-matter date '{md_date.group(1)}' from the markdown does not "
                  f"appear in the HTML; the HTML was rendered from a different revision.")
        year = md_date.group(1).rsplit(" ", 1)[-1]
        cr = re.search(r"Copyright\s+©?\s*OASIS Open\s+(\d{4})", md_text)
        if cr and cr.group(1) != year:
            f.add(WARN, "date-sync",
                  f"Copyright year {cr.group(1)} does not match the document date year "
                  f"{year}.")

    # self-referential URLs must be lowercase (case-sensitive origin)
    for u in set(re.findall(r"https://docs\.oasis-open\.org/\S+", prose)):
        path = u.split("docs.oasis-open.org/", 1)[1].rstrip(".,)\\")
        if path != path.lower() and "/templates/" not in u:
            f.add(WARN, "case",
                  f"Mixed-case path in docs.oasis-open.org URL (host is case-sensitive): {u}")


# ------------------------------------------------- DOCX-native track checks
#
# KMIP/PKCS#11-style packages: the TC's .docx is authoritative and the
# HTML/PDF are Microsoft Word renders. The markdown-track checks do not apply
# (there is no .md by design), but the format-agnostic ones do, plus a set of
# render-fidelity checks specific to the track. Provenance: the 15 Jul 2026
# KMIP v3.0 csd02 audit, where the anchor check found three dangling bookmarks
# that two human audit passes had left unvalidated, and the same day's csd01
# symlink-recursion cleanup.

def check_generator_meta(html_text: str, f: Findings) -> None:
    """DOCX-native renders must come from Microsoft Word. A LibreOffice or
    other render differs in kind from the TC's precedent (styling, size,
    metadata) and is a re-do, not a publication (KMIP csprd01, Jul 2026)."""
    m = re.search(r'<meta\s+name="?Generator"?\s+content="([^"]+)"', html_text, re.I)
    gen = m.group(1) if m else ""
    f.observe("generator", generator_meta=gen or "(absent)")
    if "Microsoft Word" not in gen:
        f.add(BLOCKER, "generator",
              f"HTML Generator is '{gen or 'absent'}'; a DOCX-native render must be "
              f"produced by Microsoft Word to match the TC's publication precedent.")


def check_vml_fallback(html_text: str, f: Findings) -> None:
    """A VML-only image is invisible in every modern browser. Word exports it
    when the source DOCX carries 'rely on VML'; each v:imagedata needs a
    paired <![if !vml]><img> fallback. Shipped live twice before this check
    (PKCS#11 v3.2 os cover, KMIP v3.0 csd01 cover)."""
    flat = html_text.replace("\r", "").replace("\n", " ")
    vml = len(re.findall(r"<v:imagedata\b", flat))
    fallbacks = len(re.findall(r"<!\[if !vml\]>\s*<img\b", flat))
    f.observe("vml-fallback", vml_images=vml, img_fallbacks=fallbacks)
    if vml and fallbacks < vml:
        f.add(BLOCKER, "vml-fallback",
              f"{vml} VML image(s) but only {fallbacks} <![if !vml]><img> fallback(s): "
              f"browsers that ignore VML show nothing (the invisible-cover-logo class). "
              f"Clear the source DOCX's relyOnVML web option and re-export.")


def check_asset_refs(stage_dir: str, html_path: str, html_text: str,
                     f: Findings) -> None:
    """Every relative src/href the HTML references must ship in the package.
    Image refs escape link-only sweeps (a DMLex diagram 404'd for 14 months
    this way); Word wraps attribute values across lines, so flatten first."""
    flat = html_text.replace("\r", "").replace("\n", "")
    refs = set(re.findall(r'(?:src|href)="([^"#]+)"', flat))
    base = os.path.dirname(os.path.abspath(html_path))
    missing = []
    for r in sorted(refs):
        # any URI scheme (https, ftp, mailto, data, ...) is external, not a
        # package-relative ref (ftp:// RFC citations false-fired before this)
        if re.match(r"(?i)[a-z][a-z0-9+.-]*:|//", r):
            continue
        target = os.path.normpath(os.path.join(base, r.split("?")[0]))
        if not os.path.exists(target):
            missing.append(r)
    f.observe("asset-refs",
              relative_refs_checked=sum(1 for r in refs if not re.match(r"(?i)[a-z][a-z0-9+.-]*:|//", r)),
              missing=len(missing))
    for r in missing[:20]:
        # /cdn-cgi/* is Cloudflare serve-time injection. It has exactly two
        # ways into a package, both wrong: the HTML was saved from a browser
        # (fix the source), or the gate was fed an edge capture instead of
        # the origin artifact (gate the zip). Stays a blocker either way;
        # the note tells the operator which mistake to go fix.
        note = (" This ref is Cloudflare serve-time injection: either the "
                "package contains browser-saved HTML, or you are gating a "
                "live-edge capture instead of the origin artifact."
                if r.startswith("/cdn-cgi/") else "")
        f.add(BLOCKER, "asset-refs",
              f"HTML references '{r}' which is not in the package; it 404s on "
              f"publication." + note)
    if len(missing) > 20:
        f.add(BLOCKER, "asset-refs", f"...and {len(missing) - 20} more missing asset refs.")


def check_html_cover(html_text: str, version: str, stage: str,
                     f: Findings) -> str:
    """Front-matter blocks parsed from the rendered HTML cover: the DOCX-native
    equivalent of the markdown front-matter checks. Returns the this-stage
    base URL for the PDF cross-check."""
    # Word front-loads hundreds of KB of styles/xml; the cover starts at <body>
    body_at = html_text.find("<body")
    cover = html_text[body_at if body_at >= 0 else 0:][:120000]
    head = re.sub(r"<[^>]+>", " ", cover)
    head = re.sub(r"&nbsp;|&#160;|\s+", " ", head)

    def urls_between(start: str, ends: list[str]) -> list[str] | None:
        m = re.search(start, head, re.I)
        if not m:
            return None
        seg = head[m.end():]
        cut = len(seg)
        for e in ends:
            m2 = re.search(e, seg, re.I)
            if m2:
                cut = min(cut, m2.start())
        return re.findall(r"https?://docs\.oasis-open\.org/[^\s\"<>]+", seg[:cut])

    this_urls = urls_between(r"This (version|stage)",
                             [r"Previous (version|stage)", r"Latest (version|stage)",
                              r"Technical Committee"])
    prev_urls = urls_between(r"Previous (version|stage)",
                             [r"Latest (version|stage)", r"Technical Committee"])
    latest_urls = urls_between(r"Latest (version|stage)",
                               [r"Technical Committee", r"Chairs?\b"])
    base = ""
    f.observe("front-matter", cover_this_urls=this_urls or "(none)",
              cover_previous_urls=prev_urls or "(none)", cover_latest_urls=latest_urls or "(none)")
    if this_urls is None or not this_urls:
        f.add(BLOCKER, "front-matter",
              "No 'This version' URL block found on the HTML cover.")
    else:
        for u in this_urls:
            if f"/{version}/" not in u or f"/{stage}/" not in u:
                f.add(BLOCKER, "front-matter",
                      f"This-version URL does not contain /{version}/ and /{stage}/: {u}")
            else:
                base = u.rsplit("/", 1)[0] + "/"
    for u in latest_urls or []:
        if f"/{stage}/" in u:
            f.add(BLOCKER, "front-matter",
                  f"Latest-version URL must point at the version root (no /{stage}/): {u}")
    m = re.fullmatch(r"([a-z]+)(\d\d)", stage)
    if m and int(m.group(2)) > 1 and not (prev_urls or []):
        f.add(BLOCKER, "previous-stage",
              f"Stage {stage} must cite its previous stage URLs; no Previous-version "
              f"block with docs.oasis-open.org URLs found on the HTML cover.")
    return base


def _first_h1(md_text: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            # strip embedded HTML (anchor spans etc.): the title is matched
            # against extracted PDF text, where markup never appears -- an
            # anchor left in made the A1 cover check match nothing, silently
            return re.sub(r"<[^>]+>", "", line.strip("# ").strip()).strip()
    return ""


# ===== AC-CONTENT-03 (conformance-structure) =====
# AC-CONTENT-03: Conformance section structure -- placement, numbered-clause
# completeness/uniqueness, and (CS->OS only) zero-tolerance clause-number
# preservation. Reuses stage_urls_from_md, read_text, strip_code_blocks,
# uri_path, hashlib, SITE (already imported/defined at module level in
# oasis_pub_check.py).

from collections import Counter
import html as _html_lib

NON_STANDARDS_TRACK_STAGES = {"cn", "cnd"}
BLOCKER_ELIGIBLE_STAGES = {"cs", "os"}  # csd defaults WARN-eligible: this
    # pipeline has no marker distinguishing internal-CSD-ballot from
    # csd-submitted-for-public-review (both share the 'csd' token), so a
    # 'csd' stage always gets the safer, non-overclaiming WARN tier. Retired
    # tokens like 'csprd' are BLOCKER-flagged elsewhere (check_stage_name's
    # RETIRED_STAGE_TOKENS) and can never legitimately reach this check.

CONFORMANCE_HEADING = re.compile(
    r"^\s*(?:(\d+(?:\.\d+)*|[A-Za-z])\.?\s+)?Conformance\b", re.IGNORECASE)
ANNEX_HEADING = re.compile(r"^(Annex|Appendix)\b", re.IGNORECASE)
BARE_INT_PREFIX = re.compile(r"^\d+$")
LEADING_NUM = re.compile(r"^\s*(\d+(?:\.\d+)*|[A-Za-z])\.?\s+")

PROFILE_HEADING_LINE = re.compile(
    r"^[ \t]*#{0,6}[ \t]*(?:\d+(?:\.\d+)*\.?[ \t]+)?"
    r"([^\n.!?]{1,80}\b(?:Profile|Level)\b[^\n.!?]{0,20})[ \t]*$",
    re.M | re.I)

# Clause identifiers, in priority order per spec algorithm step 8: (a) a
# numbered heading (decimal, e.g. '8.1'), optionally carrying a bracketed
# stable target-id ('[PREFIX-C-N]') that -- when present -- is the citable
# id (target ids are the form Statements of Use actually cite, and are
# stable across a heading's own renumbering); (b)/(c) a standalone bracketed
# target-id or an inline 'Clause N' label, but ONLY when paragraph-leading
# (anchored at a line start, optionally after a list-bullet marker or ATX
# heading marker) -- never matched mid-sentence, so an ordinary in-body
# cross-reference to another clause ('...as required by [WIDGET-C-1] above',
# '...per Clause 1 above') is never misread as a second definition of that
# clause. The bracket grammar itself is deliberately the stricter
# '<PREFIX>-C-<N>' shape (not any uppercase token) so an unrelated bracketed
# aside on a numbered heading, e.g. '8.1 [RFC2119] Normative Language',
# falls back to the heading's own decimal number rather than being misread
# as the clause id.
_TARGET_ID = r"[A-Z][A-Z0-9_-]{2,}-C-\d+"
CLAUSE_ID = re.compile(
    r"^[ \t]*#{0,6}[ \t]*(?P<num>\d+(?:\.\d+)+)\.?[ \t]*"
    rf"(?:\[(?P<bracket1>{_TARGET_ID})\])?"
    rf"|^[ \t]*(?:[-*+][ \t]+)?#{{0,6}}[ \t]*\[(?P<bracket2>{_TARGET_ID})\]"
    r"|^[ \t]*(?:[-*+][ \t]+)?Clause[ \t]+(?P<clauseword>\d+)\b",
    re.M)


def _unescape(text: str) -> str:
    """html.unescape (so '&nbsp;'/'&amp;' etc. read as the characters they
    are, not literal entity text) with the result's non-breaking spaces
    folded to plain spaces so downstream [ \\t]-class regexes still match."""
    return _html_lib.unescape(text).replace("\xa0", " ")


def _md_headings(md_text: str) -> list[tuple[int, str, int]]:
    """(level, heading text, char offset) for every ATX heading, in document
    order. Setext headings are not extracted -- a documented, bounded gap
    (rare in OASIS spec templates, which are ATX throughout). Callers pass
    code-block-stripped text (strip_code_blocks) so a fenced example
    containing '# not a real heading' is never picked up."""
    out = []
    pos = 0
    for line in md_text.splitlines(keepends=True):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip(), pos))
        pos += len(line)
    return out


def _html_headings(html_text: str) -> list[tuple[int, str, int]]:
    """(level, heading text, char offset into html_text) for every <h1>-<h6>,
    in document order -- the DOCX-native/HTML-only equivalent of
    _md_headings, mirroring how check_html_cover parses the rendered cover
    when there is no markdown source. Entities are unescaped ('&nbsp;'
    inside a heading like '8&nbsp;Conformance' reads as a real space, not
    literal markup) so the leading-number/name regexes still match."""
    out = []
    for m in re.finditer(r"<h([1-6])\b[^>]*>(.*?)</h\1>", html_text, re.I | re.S):
        text = re.sub(r"<[^>]+>", "", m.group(2))
        text = _unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        out.append((int(m.group(1)), text, m.start()))
    return out


def _leading_prefix(text: str) -> str | None:
    m = LEADING_NUM.match(text)
    return m.group(1) if m else None


def _is_annex_heading(text: str) -> bool:
    """True if TEXT is an Annex/Appendix heading, with or without its own
    leading number/letter prefix ('Annex A', 'A. Appendix', 'A Annex' all
    count) -- the ancestor-chain check must not miss a lettered/numbered
    annex heading just because ANNEX_HEADING itself only matches the bare
    word at the start."""
    if ANNEX_HEADING.match(text):
        return True
    prefix = _leading_prefix(text)
    return bool(prefix and ANNEX_HEADING.match(LEADING_NUM.sub("", text, count=1)))


def _modal_top_level(headings: list[tuple[int, str, int]]) -> tuple[int | None, bool]:
    """(modal top-level depth, confident) among bare-integer-numbered
    headings (algorithm step 4). Fewer than 3 comparable headings, or a tie
    for most-frequent level, is LOW-CONFIDENCE."""
    counts: Counter = Counter()
    for level, text, _pos in headings:
        p = _leading_prefix(text)
        if p and BARE_INT_PREFIX.fullmatch(p):
            counts[level] += 1
    if not counts:
        return None, False
    ranked = counts.most_common()
    top_level, top_count = ranked[0]
    tie = len(ranked) > 1 and ranked[1][1] == top_count
    confident = sum(counts.values()) >= 3 and not tie
    return top_level, confident


def _ancestors(headings: list[tuple[int, str, int]], idx: int) -> list[str]:
    stack: list[tuple[int, str]] = []
    for level, text, _pos in headings[:idx]:
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, text))
    return [text for _lvl, text in stack]


def _html_to_lines(fragment: str) -> str:
    """Flatten an HTML fragment to newline-delimited plain text: block
    boundaries become line breaks BEFORE tags are stripped, so a
    line-anchored (^) regex still finds heading/paragraph starts in text
    pulled from a rendered Word HTML render. Entities are unescaped
    ('&nbsp;' -> a real space) after flattening."""
    t = re.sub(r"<(h[1-6]|p|li|br|tr)\b[^>]*>", "\n", fragment, flags=re.I)
    t = re.sub(r"</(h[1-6]|p|li|tr)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _split_profiles(span: str) -> dict[str, str]:
    """Split a Conformance section's span into named-profile scopes
    (algorithm step 7), or one implicit '(default)' scope when no
    profile-naming sub-heading ('...Profile...', '...Level...') is found.
    The profile-name line pattern excludes '.', '!', '?' from the captured
    name so an ordinary prose sentence that happens to mention 'profile'
    ('This clause covers the Core Profile requirements.') is never misread
    as a profile-scope boundary -- real profile headings are short,
    unpunctuated titles."""
    marks = [(m.start(), m.group(1).strip()) for m in PROFILE_HEADING_LINE.finditer(span)]
    if not marks:
        return {"(default)": span}
    out = {}
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(span)
        out[name] = span[pos:end]
    return out


def _extract_clauses(scope_text: str) -> list[tuple[str, str]]:
    """[(clause_id, content_hash), ...] within one profile scope, in
    document order (algorithm step 8). Priority per match: a bracketed
    target id > the clause's own decimal heading number > an inline
    'Clause N' label. Content hash is a normalized (whitespace-collapsed,
    case-folded) digest of the text up to the next clause match."""
    matches = list(CLAUSE_ID.finditer(scope_text))
    out = []
    for i, m in enumerate(matches):
        cid = (m.group("bracket1") or m.group("bracket2")
               or m.group("clauseword") or m.group("num"))
        if not cid:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(scope_text)
        body = scope_text[m.end():end][:400]
        norm = re.sub(r"\s+", " ", body).strip().lower()
        out.append((cid, hashlib.sha256(norm.encode()).hexdigest()))
    return out


def _locate_and_extract(headings: list[tuple[int, str, int]], source_text: str,
                        is_html: bool
                        ) -> tuple[list, int | None, dict[str, list[tuple[str, str]]]] | None:
    """Silent placement+extraction pass (no findings): returns (candidates,
    winning_index_or_None, {profile_name: [(clause_id, content_hash), ...]})
    or None if there is no Conformance heading candidate at all. Used both
    for the current package (which then also scores placement/completeness
    against this same data) and, un-scored, for a previous-stage artifact in
    the stability sub-checks (steps 10-11) -- the SAME function, so a fix to
    placement/extraction logic can never drift between the two callers."""
    candidates = [(i, lvl, txt, pos) for i, (lvl, txt, pos) in enumerate(headings)
                  if CONFORMANCE_HEADING.match(txt)]
    if not candidates:
        return None
    modal_level, _confident = _modal_top_level(headings)
    passed = []
    for idx, lvl, txt, pos in candidates:
        prefix = _leading_prefix(txt)
        bare = prefix is None or bool(BARE_INT_PREFIX.fullmatch(prefix))
        annex = any(_is_annex_heading(a) for a in _ancestors(headings, idx))
        deeper = modal_level is not None and lvl > modal_level
        if bare and not annex and not deeper:
            passed.append((idx, lvl, txt, pos))
    winner = min(passed, key=lambda c: c[1]) if passed else min(candidates, key=lambda c: c[1])
    win_idx, win_level, _win_txt, win_pos = winner
    end_pos = len(source_text)
    for j in range(win_idx + 1, len(headings)):
        if headings[j][0] <= win_level:
            end_pos = headings[j][2]
            break
    span = source_text[win_pos:end_pos]
    if is_html:
        span = _html_to_lines(span)
    profiles: dict[str, list[tuple[str, str]]] = {}
    for pname, ptext in _split_profiles(span).items():
        profiles[pname] = _extract_clauses(ptext)
    return candidates, (win_idx if passed else None), profiles


def _fmt_clause_keys(keys) -> list[str]:
    """Render {(profile_name, clause_id), ...} as a readable sorted list:
    bare clause id for the implicit '(default)' scope, 'id [Profile Name]'
    otherwise, so a multi-profile CS->OS mismatch message stays legible
    instead of printing raw tuples."""
    out = [cid if pname == "(default)" else f"{cid} [{pname}]"
           for pname, cid in keys]
    return sorted(out)


def _resolve_previous_stage_artifact(stage_dir: str, prev_url: str
                                     ) -> tuple[str, str, bool]:
    """Best-effort fetch of a previous-stage artifact's text (algorithm
    steps 10-11). Tries the local sibling stage directory first -- the
    layout every OASIS-Docs TC repo uses, version/<stage>/<file> -- which
    keeps fixtures and pre-publish local runs fully offline; falls back to
    a network fetch of the published URL, skipped under PUB_CHECK_OFFLINE
    (same guard as check_revision_collision). Returns (prev_stage_token,
    text, is_html_artifact); ('', '', False) if unresolvable. is_html
    tells the caller whether to parse the resolved text with the markdown
    or the HTML heading extractor -- a Previous-stage link commonly points
    at a DOCX-native (.html) artifact even when the current package is
    markdown, or vice versa across a lineage that changed authoring track;
    parsing an HTML artifact as markdown finds zero headings and silently
    treats a fully-resolvable, consistent baseline as if every clause had
    been dropped."""
    path = uri_path(prev_url)
    parts = [p for p in path.rstrip("/").split("/") if p]
    if len(parts) < 2:
        return "", "", False
    filename, prev_stage = parts[-1], parts[-2]
    is_html_artifact = filename.lower().endswith((".html", ".htm"))
    version_root = os.path.dirname(os.path.normpath(stage_dir))
    local = os.path.join(version_root, prev_stage, filename)
    if os.path.isfile(local):
        try:
            return prev_stage, read_text(local), is_html_artifact
        except OSError:
            pass  # fall through to the network path below
    if os.getenv("PUB_CHECK_OFFLINE", "").lower() in {"1", "true", "yes"}:
        return prev_stage, "", is_html_artifact
    import urllib.error
    import urllib.request
    try:
        req = urllib.request.Request(prev_url, headers={"User-Agent": "pub-check"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return prev_stage, r.read().decode("utf-8", errors="replace"), is_html_artifact
    except Exception:  # noqa: BLE001 - unresolvable prior artifact, not a crash
        return prev_stage, "", is_html_artifact

def check_conformance_structure(md_text: str, html_text: str, stage_dir: str,
                                stage: str, f: Findings) -> None:
    """AC-CONTENT-03: where a Standards Track Conformance section is
    present, it must be a separate top-level numbered section (not buried
    in an Annex/Appendix or a deeper subsection) populated with
    individually and uniquely numbered clauses. Severity is stage-gated:
    BLOCKER at cs/os (and, were it distinguishable, csd-submitted-for-
    public-review -- this pipeline has no such marker, so 'csd' stays
    WARN-eligible), WARN at wd/csd. General clause-number stability across
    any OTHER adjacent-stage transition is WARN-tier (Guidelines-sourced,
    not TC-Process-mandatory); at CS->OS specifically the clause NUMBER SET
    (scoped per conformance profile, so a whole profile silently dropped
    while another profile happens to reuse its numbers is still caught) is
    zero-tolerance BLOCKER (TC Process 2.9), while a wording change under a
    stable number there is a manual-review WARN, not an automatic reject
    (TC Process 2.2.4 permits coordinated non-material changes). Skipped
    entirely for Non-Standards Track work products (Committee Notes/
    Technical Reports, stage tokens cn/cnd): TC Process does not require a
    conformance section there at all."""
    md_text = md_text or ""
    html_text = html_text or ""
    stage = stage or ""
    stage_dir = stage_dir or ""

    stage_m = re.match(r"([a-z]+)", stage)
    stage_prefix = stage_m.group(1) if stage_m else stage
    if stage_prefix in NON_STANDARDS_TRACK_STAGES:
        f.observe("conformance-structure", stage_prefix=stage_prefix,
                  track="Non-Standards Track: skipped, not required per TC Process")
        return

    is_html = not bool(md_text)
    if md_text:
        source_text = strip_code_blocks(md_text, "md")
        headings = _md_headings(source_text)
    elif html_text:
        source_text = strip_code_blocks(html_text, "html")
        headings = _html_headings(source_text)
    else:
        source_text = ""
        headings = []
    if not headings:
        f.observe("conformance-structure", stage_prefix=stage_prefix, headings_scanned=0)
        return

    candidates = [(i, lvl, txt, pos) for i, (lvl, txt, pos) in enumerate(headings)
                  if CONFORMANCE_HEADING.match(txt)]
    f.observe("conformance-structure", stage_prefix=stage_prefix,
              headings_scanned=len(headings), conformance_candidates=len(candidates))
    if not candidates:
        return  # the sibling 'No Conformance section found' check owns bare absence

    blocker_eligible = stage_prefix in BLOCKER_ELIGIBLE_STAGES
    modal_level, confident = _modal_top_level(headings)
    f.observe("conformance-structure",
              modal_top_level=modal_level if modal_level is not None else "(none)",
              modal_confidence="high" if confident else "low")

    # Current-package placement + extraction: the SAME helper used for the
    # previous-stage artifact below, so a placement/extraction fix can never
    # apply to one side and not the other.
    result = _locate_and_extract(headings, source_text, is_html)
    _candidates_again, passed_win_idx, profiles = result  # candidates non-empty above -> never None

    placement_sev = BLOCKER if (blocker_eligible and confident) else WARN
    if passed_win_idx is None:
        best = min(candidates, key=lambda c: c[1])
        low_conf = ("" if confident else " (low-confidence depth signal: fewer than 3 "
                    "comparable top-level headings, or a tie -- capped at WARN)")
        f.add(placement_sev, "conformance-structure",
              f"Conformance section is a buried subsection: '{best[2]}' is nested "
              f"deeper than the document's top-level numbered sections (or sits "
              f"under an Annex/Appendix), not a separate top-level numbered "
              f"section.{low_conf}")

    completeness_sev = BLOCKER if blocker_eligible else WARN
    for pname, clauses in profiles.items():
        label = f" (profile '{pname}')" if pname != "(default)" else ""
        if not clauses:
            f.add(WARN, "conformance-structure",
                  f"Conformance section{label} is not populated with numbered "
                  f"clauses: no clause identifiers were extracted.")
            continue
        seen: dict[str, int] = {}
        for cid, _h in clauses:
            seen[cid] = seen.get(cid, 0) + 1
        for cid, n in sorted(seen.items()):
            if n > 1:
                f.add(completeness_sev, "conformance-structure",
                      f"Duplicate clause number{label}: '{cid}' appears {n} times.")
    total_clauses = sum(len(c) for c in profiles.values())
    f.observe("conformance-structure", profiles_found=len(profiles),
              clauses_extracted=total_clauses)

    # ---- stability, algorithm steps 10-12 --------------------------------
    if is_html:
        # Known, documented gap: check_html_cover parses a Previous-stage
        # URL off the rendered HTML cover for ITS OWN findings but does not
        # expose it to this check, and duplicating that cover-parse here
        # was out of scope for this pass (see notes). Reported honestly as
        # unsupported, never mislabeled as a first-publication no-op.
        f.observe("conformance-structure",
                  stability="not verified (DOCX-native track: Previous-stage URL "
                            "extraction from the HTML cover is not wired into "
                            "this check -- known, documented gap)")
        return
    prev_urls = [u for u in stage_urls_from_md(md_text, "Previous") if u.startswith(SITE + "/")]
    if not prev_urls:
        f.observe("conformance-structure", stability="no-op (first publication)")
        return
    prev_url = prev_urls[0]
    if len(prev_urls) > 1:
        md_matches = [u for u in prev_urls if uri_path(u).lower().endswith(".md")]
        if md_matches:
            prev_url = md_matches[0]
    prev_stage, prev_text, prev_is_html = _resolve_previous_stage_artifact(stage_dir, prev_url)
    prev_stage_m = re.match(r"([a-z]+)", prev_stage) if prev_stage else None
    prev_stage_prefix = prev_stage_m.group(1) if prev_stage_m else ""
    cs_to_os = stage_prefix == "os" and prev_stage_prefix == "cs"
    f.observe("conformance-structure", previous_stage_url=prev_url,
              previous_stage_resolved=bool(prev_text),
              previous_stage_is_html=prev_is_html, cs_to_os_transition=cs_to_os)

    def _extract_prev_profiles() -> dict[str, list[tuple[str, str]]]:
        if not prev_text:
            return {}
        kind = "html" if prev_is_html else "md"
        prev_source = strip_code_blocks(prev_text, kind)
        prev_headings = _html_headings(prev_source) if prev_is_html else _md_headings(prev_source)
        prev_result = _locate_and_extract(prev_headings, prev_source, prev_is_html)
        return prev_result[2] if prev_result else {}

    if cs_to_os:
        if not prev_text:
            f.add(BLOCKER, "conformance-structure",
                  f"Cannot verify CS-preservation requirement: the approved CS "
                  f"baseline ({prev_url}) could not be resolved. Manual "
                  f"confirmation is required before OS approval can be "
                  f"finalized (TC Process section 2.9).")
            return
        prev_profiles = _extract_prev_profiles()
        prev_keys = {(pname, cid) for pname, clauses in prev_profiles.items()
                     for cid, _h in clauses}
        cur_keys = {(pname, cid) for pname, clauses in profiles.items()
                    for cid, _h in clauses}
        if prev_keys != cur_keys:
            f.add(BLOCKER, "conformance-structure",
                  f"OS conformance clause numbering differs from approved CS: "
                  f"CS carried {_fmt_clause_keys(prev_keys)}, OS carries "
                  f"{_fmt_clause_keys(cur_keys)}. TC Process section 2.9 requires "
                  f"the clause number set be preserved unchanged from the "
                  f"approved Committee Specification.")
            return
        prev_map = {(pname, cid): h for pname, clauses in prev_profiles.items()
                    for cid, h in clauses}
        cur_map = {(pname, cid): h for pname, clauses in profiles.items()
                   for cid, h in clauses}
        for key in sorted(prev_keys):
            if prev_map[key] != cur_map[key]:
                pname, cid = key
                label = f" (profile '{pname}')" if pname != "(default)" else ""
                f.add(WARN, "conformance-structure",
                      f"OS conformance clause wording differs from approved CS "
                      f"under a stable number{label} ({cid}): confirm this was "
                      f"coordinated with the TC Administrator as a non-material "
                      f"change (TC Process section 2.2.4) with a TC-mailing-list "
                      f"summary, or treat it as material and out of process for "
                      f"this stage.")
        return

    if not prev_text:
        f.add(WARN, "conformance-structure",
              f"Stability not verified - previous stage unavailable: could not "
              f"resolve or fetch {prev_url} to diff conformance clause numbers.")
        return
    prev_profiles = _extract_prev_profiles()
    cur_map = {(pname, cid): h for pname, clauses in profiles.items() for cid, h in clauses}
    cur_hash_to_keys: dict[str, set] = {}
    for key, h in cur_map.items():
        cur_hash_to_keys.setdefault(h, set()).add(key)
    for pname, clauses in prev_profiles.items():
        label = f" (profile '{pname}')" if pname != "(default)" else ""
        for cid, phash in clauses:
            key = (pname, cid)
            if key not in cur_map:
                f.add(WARN, "conformance-structure",
                      f"Clause number removed/renumbered{label}: '{cid}' was "
                      f"present in the previous stage but is absent from this "
                      f"stage.")
            elif cur_map[key] != phash:
                movers = cur_hash_to_keys.get(phash, set()) - {key}
                if movers:
                    f.add(WARN, "conformance-structure",
                          f"Clause silently renumbered{label}: '{cid}' content "
                          f"now appears under {_fmt_clause_keys(movers)} instead.")


# ===== AC-CONTENT-05 (references-split) =====
REFERENCES_NUM_PREFIX = re.compile(
    r"^(?:(?:Annex|Appendix)\s+)?(?:\d+(?:\.\d+)*\.?|[A-Za-z](?:\.\d+)*\.?)\s+",
    re.IGNORECASE)

REFERENCES_ID_RE = re.compile(r"^[#*\\\s]*\[([^\[\]\r\n]+)\]", re.M)

REFERENCES_STANDARDS_TRACK_STAGES = {"csd", "cs", "os", "errata"}


def _norm_references_heading(text: str) -> str:
    """Strip a numbering/Annex prefix, trailing punctuation, collapse
    whitespace, lowercase. Deliberately does not strip ordinary leading
    words (the required token must be all-digit or a single letter), so
    'Normative References' is never mis-normalized to 'references'."""
    text = REFERENCES_NUM_PREFIX.sub("", text.strip())
    text = re.sub(r"\s+", " ", text).strip().rstrip(".:;,")
    return text.lower()


def _references_headings_md(md_text: str) -> list:
    out = []
    for m in re.finditer(r"^(#{1,3})[ \t]+(.*?)[ \t]*$", md_text, re.M):
        raw = m.group(2).strip()
        # Optional CommonMark ATX closing sequence ("## Heading ##"): must be
        # preceded by whitespace, so this never eats a heading that legitimately
        # ends in a bare '#' with no preceding space.
        raw = re.sub(r"[ \t]+#+[ \t]*$", "", raw)
        out.append({"level": len(m.group(1)), "raw": raw,
                    "norm": _norm_references_heading(raw),
                    "start": m.start(), "content_start": m.end()})
    return out


def _references_headings_html(html_text: str) -> list:
    out = []
    for m in re.finditer(r"<h([1-3])\b[^>]*>(.*?)</h\1>", html_text, re.I | re.S):
        raw = re.sub(r"&nbsp;|&#160;", " ", re.sub(r"<[^>]+>", " ", m.group(2)))
        raw = re.sub(r"\s+", " ", raw).strip()
        out.append({"level": int(m.group(1)), "raw": raw,
                    "norm": _norm_references_heading(raw),
                    "start": m.start(), "content_start": m.end()})
    return out


def _references_span(headings: list, i: int, text_len: int):
    start = headings[i]["content_start"]
    end = text_len
    for j in range(i + 1, len(headings)):
        if headings[j]["level"] <= headings[i]["level"]:
            end = headings[j]["start"]
            break
    return start, end


def _references_children(headings: list, i: int, span_end: int) -> list:
    level = headings[i]["level"]
    return [j for j in range(i + 1, len(headings))
            if headings[j]["start"] < span_end and headings[j]["level"] == level + 1]


def _references_ids(text: str, is_html: bool) -> list:
    if is_html:
        text = re.sub(r"(?i)</(p|li|div|tr|h[1-6])>|<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;|&#160;", " ", text)
    ids = []
    for m in REFERENCES_ID_RE.finditer(text):
        rid = m.group(1).strip().rstrip("\\").strip()
        if rid:
            ids.append(rid)
    return ids

def check_references_split(stage: str, md_text: str, html_text: str, f: Findings) -> None:
    """AC-CONTENT-05 (WARN; handbook-WPQualityChecklist.txt editorial quality
    verification checklist: 'normative references listed separately from
    informative references'). On a Standards Track work product, if the
    document has a References section at all, it should split into
    separately labeled Normative/Informative headings, and no reference ID
    should be listed under both. Labeling/structure convention only -- this
    does not judge whether a reference's true normative-vs-informative
    status matches its heading placement (that would require cross-checking
    which references numbered conformance clauses actually depend on).
    Fires only for Standards Track stage tokens (csd, cs, os, errata) per
    handbook-WPQualityChecklist.txt / handbook-Maintenance.txt; Non-Standards
    Track (cnd, cn) and unrecognized tokens (e.g. wd) are skipped entirely --
    naming-directives.txt: a Non-Standards Track Work Product 'does not
    contain normative statements that define mandatory conformance
    requirements', so the split has no meaning there. Heading detection
    covers markdown ATX headings (#, ##, ###), tolerating an optional ATX
    closing hash sequence, and, on the DOCX-native track with no markdown
    source, rendered <h1>-<h3> HTML; markdown setext headings are not
    produced by the OASIS template and are not handled. Inputs that are not
    strings (a malformed/None stage or text) are treated as absent rather
    than raised on. Both text sources are run through the tool's
    strip_code_blocks() first so an illustrative fenced/`<pre>`-`<code>`
    example containing a decoy heading or bracketed ID is never scanned as
    real document structure."""
    stage = stage if isinstance(stage, str) else ""
    md_text = strip_code_blocks(md_text, "md") if isinstance(md_text, str) else ""
    html_text = strip_code_blocks(html_text, "html") if isinstance(html_text, str) else ""

    prefix_m = re.match(r"[a-z]+", stage)
    prefix = prefix_m.group(0) if prefix_m else ""
    is_standards_track = prefix in REFERENCES_STANDARDS_TRACK_STAGES
    f.observe("references-split", stage_prefix=prefix or "(none)",
              stage_track="standards" if is_standards_track else "non-standards/unrecognized (skipped)")
    if not is_standards_track:
        return

    if md_text:
        headings, source, is_html = _references_headings_md(md_text), md_text, False
    elif html_text:
        headings, source, is_html = _references_headings_html(html_text), html_text, True
    else:
        f.observe("references-split", source_present=False, references_headings_found=0)
        return

    classified = []
    for h in headings:
        kind = {"references": "bare", "normative references": "norm",
                "informative references": "info"}.get(h["norm"], "other")
        classified.append({**h, "kind": kind})

    if not any(h["kind"] in ("bare", "norm", "info") for h in classified):
        f.observe("references-split", references_headings_found=0)
        return

    f.observe("references-split",
              references_headings_found=[h["raw"] for h in classified if h["kind"] != "other"])

    for i, h in enumerate(classified):
        if h["kind"] != "bare":
            continue
        span_start, span_end = _references_span(classified, i, len(source))
        kids = _references_children(classified, i, span_end)
        direct_end = classified[kids[0]]["start"] if kids else span_end
        direct_ids = sorted(set(_references_ids(source[span_start:direct_end], is_html)))
        has_split_child = any(classified[k]["kind"] in ("norm", "info") for k in kids)
        if not direct_ids and has_split_child:
            continue  # pure container for a nested differentiated split
        if len(direct_ids) >= 2:
            f.add(WARN, "references-split",
                  f"References heading '{h['raw']}' is not labeled Normative References / "
                  f"Informative References ({len(direct_ids)} references listed under a "
                  f"single undifferentiated heading) -- confirm each entry's "
                  f"normative/informative classification and split accordingly.")

    norm_idx = [i for i, h in enumerate(classified) if h["kind"] == "norm"]
    info_idx = [i for i, h in enumerate(classified) if h["kind"] == "info"]
    if norm_idx and info_idx:
        norm_ids = set()
        for i in norm_idx:
            s, e = _references_span(classified, i, len(source))
            norm_ids.update(_references_ids(source[s:e], is_html))
        info_ids = set()
        for i in info_idx:
            s, e = _references_span(classified, i, len(source))
            info_ids.update(_references_ids(source[s:e], is_html))
        dupes = sorted(norm_ids & info_ids)
        f.observe("references-split", normative_reference_ids=len(norm_ids),
                  informative_reference_ids=len(info_ids),
                  cross_list_duplicates=dupes or "(none)")
        for rid in dupes:
            f.add(WARN, "references-split",
                  f"Reference [{rid}] is listed under both Normative References and "
                  f"Informative References -- confirm this is not an editorial "
                  f"duplication or misclassification.")


# ===== AC-CONTENT-08 (content-labels) =====
# AC-CONTENT-08: content-type labeling of Examples/Appendix/Annex headings.

STRIP_HEADING_NUM_RE = re.compile(r"^[A-Z0-9]+(?:\.[A-Z0-9]+)*\.?\s+")

EXAMPLE_HEADING_RE = re.compile(
    r"(?i)^(examples?|illustrative\s+examples?|"
    r"sample\s+(?:\S+\s+)?(?:requests?|responses?|messages?|payloads?|documents?|"
    r"configurations?|files?|data|code|instances?|outputs?|inputs?|records?))\b")

APPENDIX_HEADING_RE = re.compile(r"(?i)^(appendix|annex)\b")

_DASH_TRANSLATE = str.maketrans({
    "‐": "-",  # hyphen
    "‑": "-",  # non-breaking hyphen
    "‒": "-",  # figure dash
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # minus sign
})


def _normalize_dashes(text: str) -> str:
    """Fold Unicode hyphen/dash variants to ASCII '-' so a heading like
    'Examples (Non-normative)' typed with a non-breaking hyphen, or an
    em-dash suffix separator, still matches the marker regex, which is
    authored against the ASCII form."""
    return text.translate(_DASH_TRANSLATE)


_MARKER = r"(?:non[-\s]?normative|(?<![\w-])informative|(?<![\w-])normative)"
# The bare 'informative'/'normative' alternatives require the character
# immediately before the match NOT be a word char or hyphen, so a compound
# like 'anti-normative' or 'quasi-normative' cannot satisfy the label test
# via a \b match on the tail of the word; 'non-normative' is matched by its
# own alternative and is unaffected by this guard.

HEADING_SUFFIX_LABEL_RE = re.compile(
    r"(?i)(?:\(\s*" + _MARKER + r"\s*\)|[-–—:]\s*" + _MARKER + r"\s*)$")

SENTENCE_LEAD_PREFIX_RE = re.compile(
    r"(?i)^(?:this\s+(?:appendix|annex|section|example)\s+is|it\s+is)\s+")

SENTENCE_MARKER_START_RE = re.compile(r"(?i)^" + _MARKER + r"\b")

# Terminal punctuation is mandatory for the predicate-final branch: the
# spec's algorithm step 6(ii)(b) requires the marker be "the final word ...
# immediately before the terminal punctuation". An optional '?' here would
# let a body block that has no sentence terminator at all (or is truncated
# at the 200-char cap with a marker as the last captured word) falsely
# satisfy the rule.
SENTENCE_MARKER_END_RE = re.compile(r"(?i)\b" + _MARKER + r"\b[.!]\s*$")

BLANKET_LABEL_RE = re.compile(
    r"(?i)(?<!not\s)\b(?:all|these|every)\s+"
    r"(appendi(?:x|xes|ces)|annexes?|examples?)\b"
    r"[^.]{0,120}\b" + _MARKER + r"\b")
# (?<!not\s) rejects negated forms ('Not all examples...') so a negated
# sentence cannot be mistaken for a blanket labeling statement; 'appendices'
# (the plural the cited handbook quote itself actually uses, 'Appendices and
# examples...') is now recognized alongside 'appendix'/'appendixes'.

NON_STANDARDS_TRACK_PREFIXES = {"cnd", "cn"}

# Common abbreviations whose internal period is not a sentence end, so the
# 200-char first-sentence scan does not stop early inside 'e.g.' / 'i.e.' /
# etc. immediately before reaching the real label.
_ABBREV_TAIL_RE = re.compile(r"(?i)\b(?:e\.g|i\.e|etc|cf|vs|fig|eq|no|approx|resp)\.$")


def _md_content_headings(prose: str) -> list[tuple[int, str, str, str]]:
    """ATX + setext headings from code-stripped markdown, each paired with its
    line number and the raw text of the body block immediately following it
    (up to the next heading), for the first-sentence structural test. Allows
    up to 3 leading spaces before an ATX marker, per CommonMark."""
    lines = prose.splitlines()
    n = len(lines)
    raw = []  # (level, title, start_idx0, end_idx0_exclusive)
    i = 0
    while i < n:
        line = lines[i]
        m = re.match(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            raw.append((len(m.group(1)), m.group(2).strip(), i, i + 1))
            i += 1
            continue
        if line.strip() and i + 1 < n:
            nxt = lines[i + 1].strip()
            if re.fullmatch(r"=+", nxt):
                raw.append((1, line.strip(), i, i + 2))
                i += 2
                continue
            if re.fullmatch(r"-{2,}", nxt):
                raw.append((2, line.strip(), i, i + 2))
                i += 2
                continue
        i += 1
    out = []
    for idx, (level, title, _start, end) in enumerate(raw):
        next_start = raw[idx + 1][2] if idx + 1 < len(raw) else n
        body = "\n".join(lines[end:next_start])
        out.append((level, title, f"line {raw[idx][2] + 1}", body))
    return out


class _HeadingParser(HTMLParser):
    """Collect h1-h6 elements in document order, each with the text of the
    block that follows it up to the next heading. An HTMLParser walk (not a
    single monolithic regex over the whole document) so malformed/unclosed
    heading markup cannot force pathological backtracking, and so entities
    (&mdash;, &nbsp;, ...) decode for free via convert_charrefs -- mirrors
    the codebase's existing HTMLParser precedent (_AnchorParser) rather than
    reimplementing tag matching in regex."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[list] = []  # [level, [title parts], [body parts], pos]
        self._level: int | None = None

    def handle_starttag(self, tag, attrs):
        if len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            line, _col = self.getpos()
            self.headings.append([int(tag[1]), [], [], f"line {line}"])
            self._level = int(tag[1])

    def handle_endtag(self, tag):
        if self._level is not None and tag == f"h{self._level}":
            self._level = None

    def handle_data(self, data):
        if not self.headings:
            return
        if self._level is not None:
            self.headings[-1][1].append(data)
        else:
            self.headings[-1][2].append(data)


def _html_content_headings(html_text: str) -> list[tuple[int, str, str, str]]:
    """h1-h6 elements from code-stripped rendered HTML, document order, each
    paired with the text of the block immediately following it (up to the
    next heading), for the DOCX-native track."""
    parser = _HeadingParser()
    try:
        parser.feed(html_text.replace("\r", ""))
    except Exception:
        return []
    out = []
    for level, title_parts, body_parts, pos in parser.headings:
        title = re.sub(r"\s+", " ", "".join(title_parts)).strip()
        body = re.sub(r"\s+", " ", "".join(body_parts)).strip()
        out.append((level, title, pos, body))
    return out


def _first_sentence(body: str) -> str:
    """The first sentence of a body block, capped at 200 characters, ending
    at the first real sentence-terminal '.'/'!'. A '.' immediately followed
    by a digit (a decimal point inside a version id like 'v1.2') or preceded
    by a common abbreviation ('e.g.', 'i.e.', ...) is not treated as a
    sentence end, so prose that happens to contain a version number is not
    mis-split before it reaches its actual label."""
    body = body.lstrip()
    blank = re.search(r"\n\s*\n", body)
    if blank:
        body = body[:blank.start()]
    body = body[:200]
    for m in re.finditer(r"[.!]", body):
        pos = m.start()
        if pos + 1 < len(body) and body[pos + 1].isdigit():
            continue
        if _ABBREV_TAIL_RE.search(body[:pos + 1]):
            continue
        return body[:pos + 1].strip()
    return body.strip()


def _sentence_labels(sentence: str) -> bool:
    s = sentence.strip()
    if not s:
        return False
    core = SENTENCE_LEAD_PREFIX_RE.sub("", s, count=1)
    if SENTENCE_MARKER_START_RE.match(core):
        return True
    return bool(SENTENCE_MARKER_END_RE.search(s))

def check_content_labels(md_text: str, html_text: str, stage: str, f: Findings) -> None:
    """AC-CONTENT-08: every heading designating worked Examples (Examples,
    Illustrative Examples, curated 'Sample <noun>' titles) should carry an
    explicit content-type label -- handbook-Conformance.txt classifies
    Examples as non-normative content and its own content-type table says it
    'should be clearly labelled'. The label may sit on the heading itself
    ('(Non-normative)'), as the lead/predicate of the first sentence
    following the heading, be inherited from a labeled ancestor heading, or
    come from a document-wide blanket statement. Appendix/Annex headings get
    the identical structural test but only ever produce a non-scoring INFO
    advisory note: the cited policy only obligates labeling of appendices
    that are NOT part of the conformance requirements, and this checker
    cannot tell which appendices are actually normative. Gated off the
    Non-Standards Track (cnd/cn Committee Notes): the whole document is
    already non-normative there, so no appendix can be mistaken for a
    binding conformance requirement."""
    stage_l = stage.lower() if isinstance(stage, str) else ""
    m = re.fullmatch(r"([a-z]+)(\d\d)?", stage_l)
    prefix = m.group(1) if m else stage_l
    if prefix in NON_STANDARDS_TRACK_PREFIXES:
        f.observe("content-labels", track=f"non-standards ({stage}, skipped)")
        return

    if md_text:
        prose = strip_code_blocks(md_text, "md")
        headings = _md_content_headings(prose)
        blanket_prose = prose
        source = "markdown"
    elif html_text:
        stripped_html = strip_code_blocks(html_text, "html")
        headings = _html_content_headings(stripped_html)
        blanket_prose = re.sub(r"<[^>]+>", " ", stripped_html)
        source = "HTML"
    else:
        f.observe("content-labels", track="(no source)", headings_scanned=0)
        return

    blanket_prose = _normalize_dashes(blanket_prose)
    blanket_classes: set[str] = set()
    blanket_notes: dict[str, str] = {}
    for bm in BLANKET_LABEL_RE.finditer(blanket_prose):
        cls = "example" if bm.group(1).lower().startswith("example") else "appendix"
        blanket_classes.add(cls)
        blanket_notes.setdefault(cls, re.sub(r"\s+", " ", bm.group(0)).strip())

    blanket_used: set[str] = set()
    example_candidates = example_unlabeled = 0
    appendix_candidates = appendix_unlabeled = 0
    stack: list[tuple[int, bool]] = []
    for level, raw_title_orig, pos, body_orig in headings:
        raw_title = _normalize_dashes(raw_title_orig)
        body = _normalize_dashes(body_orig)
        while stack and stack[-1][0] >= level:
            stack.pop()
        ancestor_labeled = any(labeled for _lvl, labeled in stack)
        title = STRIP_HEADING_NUM_RE.sub("", raw_title, count=1).strip()
        if EXAMPLE_HEADING_RE.match(title):
            kind = "example"
        elif APPENDIX_HEADING_RE.match(title):
            kind = "appendix"
        else:
            kind = None
        direct_labeled = False
        if kind:
            if HEADING_SUFFIX_LABEL_RE.search(title):
                direct_labeled = True
            elif _sentence_labels(_first_sentence(body)):
                direct_labeled = True
        blanket_hit = bool(kind) and kind in blanket_classes
        satisfied = direct_labeled or (bool(kind) and ancestor_labeled) or blanket_hit
        stack.append((level, direct_labeled))
        if kind == "example":
            example_candidates += 1
            if not satisfied:
                example_unlabeled += 1
                f.add(WARN, "content-labels",
                      f"Examples-pattern heading '{raw_title_orig}' ({source} {pos}) carries no "
                      f"content-type label (heading suffix, first-sentence statement, labeled "
                      f"ancestor heading, or document-wide blanket statement): the Handbook "
                      f"classifies Examples as non-normative content and says it should be "
                      f"clearly labelled 'Non-normative' (or 'Informative').")
            elif blanket_hit and not direct_labeled and not ancestor_labeled:
                blanket_used.add(kind)
        elif kind == "appendix":
            appendix_candidates += 1
            if not satisfied:
                appendix_unlabeled += 1
                f.add(INFO, "content-labels",
                      f"Appendix/Annex heading '{raw_title_orig}' ({source} {pos}) carries no "
                      f"content-type label. Advisory only: confirm whether this appendix/annex "
                      f"is part of the conformance requirements, and if not, label it "
                      f"'Non-normative' per handbook-Conformance.txt.")
            elif blanket_hit and not direct_labeled and not ancestor_labeled:
                blanket_used.add(kind)

    for cls, sentence_text in blanket_notes.items():
        if cls in blanket_used:
            f.add(INFO, "content-labels",
                  f"Document-wide blanket {cls} content-type statement found, relied on to "
                  f"satisfy unlabeled {cls} headings: \"{sentence_text}\"")
        else:
            f.add(INFO, "content-labels",
                  f"Document-wide blanket {cls} content-type statement found (no unlabeled "
                  f"{cls} heading needed it): \"{sentence_text}\"")

    f.observe("content-labels", track=source, headings_scanned=len(headings),
              example_candidates=example_candidates, example_unlabeled=example_unlabeled,
              appendix_candidates=appendix_candidates, appendix_unlabeled=appendix_unlabeled,
              blanket_statement_classes=sorted(blanket_classes) or "(none)")


# ===== AC-FRONTMATTER-07 (stage-token) =====
# AC-FRONTMATTER-07: stage-abbreviation token extraction from a
# docs.oasis-open.org URL, per naming-directives.txt 6.1 (Multi-Part Option 1
# part-segment) and 6.2 (Previous/Latest stage URI shape). Reuses
# VALID_STAGE_PREFIXES / RETIRED_STAGE_TOKENS -- the same vocabulary the
# 'stage-name' check already defines -- rather than a new list.
_STAGE_TOKEN_VOCAB = "|".join(sorted(VALID_STAGE_PREFIXES | RETIRED_STAGE_TOKENS))
_STAGE_DIR_TOKEN = re.compile(rf"^(?:{_STAGE_TOKEN_VOCAB})(?:\d{{2}})?$", re.IGNORECASE)
_STAGE_STEM_TOKEN = re.compile(rf"^(?:{_STAGE_TOKEN_VOCAB})\d{{2}}$", re.IGNORECASE)
# Multi-Part Option 1 part-subdirectory shape (naming-directives.txt 6.1):
# alnum start/end, internal periods/hyphens allowed -- the same partName
# grammar the part-numbering check family (AC-NAMING-20) already uses, not
# the narrower [a-z0-9-]+ a first draft used, which failed to step past a
# part-segment whose partName legitimately carries a period (adversary
# MAJOR: 'Multi-Part Option 1 directory detection').
_PART_SEGMENT = re.compile(r"^part\d+-[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$",
                            re.IGNORECASE)
# Prose/markup trailing characters neither stage_urls_from_md's own lazy
# regex (stops only at ')'/whitespace/backslash) nor an HTML-cover URL scan
# (stops only at whitespace/quote/angle-bracket) excludes, so a
# sentence-final period, comma, semicolon, or bracket routinely rides along
# with an extracted cover-page URL. Stripped once, before both token
# extraction and display, so detection and the printed URL always agree
# (adversary BLOCKER: 'trailing prose punctuation').
_TRAILING_URL_PUNCT = ".,;:)]}'\">"


def _clean_url(u: str) -> str:
    """Canonicalize a URL pulled out of surrounding prose: drop a wrapping
    '(' / '<' and any trailing punctuation that is prose formatting, not
    part of the URI. naming-directives.txt s3 permits only alphanumerics,
    '.', and '-' in a filename/directory name, and separately bars a
    filename or directory name from beginning or ending with a punctuation
    character at all, so a real path component can never legitimately END
    in '.', ',', ')', etc. -- stripping these can never remove real path
    content, only prose formatting the extraction regexes did not exclude."""
    u = u.strip()
    while u and u[0] in "(<":
        u = u[1:]
    while u and u[-1] in _TRAILING_URL_PUNCT:
        u = u[:-1]
    return u


def _bare_stage_token(tok: str) -> str:
    """Strip a trailing revision number, case-normalized for comparison only
    (case defects themselves are the existing 'case' checks' job)."""
    return re.sub(r"\d+$", "", tok).lower()


def _extract_stage_tokens(url: str) -> tuple[str | None, str | None]:
    """naming-directives.txt 6.1/6.2 token extraction: (directory-position
    candidate, filename-stem-position candidate) for a Previous/Latest-stage
    URL. Operates on uri_path(url) -- the same percent-decoded, query/
    fragment-stripped path every other URI-character check in this file
    uses -- so an encoded %63sd%30%31 reads as the csd01 it decodes to
    (adversary BLOCKER: 'URL parsing' / percent-encoding evasion).

    Directory position steps past a Multi-Part Option 1 part-segment
    ([partNumber]-[partName]) to the segment one level further up, and is
    only computed when the URL actually names a file: a bare directory
    reference (.../csd01/, no filename) has no filename-stem position to
    mis-extract from, so a trailing-slash URL is read purely as a directory
    candidate and never re-interpreted as a filename stem (adversary MAJOR:
    'trailing-slash or no-filename URLs' false positive).

    Filename-stem position splits on '-' OR '.' -- naming-directives.txt s3
    filenames legitimately embed '.' inside a version segment like v1.0, and
    a filename that merges the version and stage with '.' instead of '-'
    (e.g. ourSpec-v2.0.csd01.html) still needs the embedded token caught --
    and requires a 2-digit revision suffix so an ordinary WP-abbrev/partName
    word never false-matches a bare stage word (naming-directives.txt 6.2's
    worked example never uses a stage revision other than exactly 2 digits;
    this bound is the check-spec's own deliberate anti-collision design,
    step 4c, kept as-is here -- see rebuttals for the adversary's ask to
    widen it further to bare/3-digit/no-delimiter tokens).

    The '.' assumed to separate a real extension is only stripped when what
    follows it looks like one (1-5 letters): a bare, extensionless
    Previous/Latest URI whose only period is the one inside its OWN version
    segment (…-v2.0-csprd01, no trailing .html) must not have that version
    period mistaken for an extension separator and the real token discarded
    with the 'extension' -- a failure mode a naive rsplit('.', 1) hits the
    moment prose punctuation (comma, period) rides along after a stage
    token with no real extension present."""
    path = uri_path(url)
    segs = [s for s in path.split("/") if s]
    if not segs:
        return None, None
    if path.endswith("/"):
        d = segs[-1]
        return (d if _STAGE_DIR_TOKEN.fullmatch(d) else None), None
    fn = segs[-1]
    last_dot = fn.rfind(".")
    stem = fn[:last_dot] if last_dot > 0 and re.fullmatch(r"[A-Za-z]{1,5}", fn[last_dot + 1:]) else fn
    dir_cand = None
    if len(segs) >= 2:
        d = segs[-2]
        if _STAGE_DIR_TOKEN.fullmatch(d):
            dir_cand = d
        elif (_PART_SEGMENT.fullmatch(d) and len(segs) >= 3
              and _STAGE_DIR_TOKEN.fullmatch(segs[-3])):
            dir_cand = segs[-3]
    stem_cand = None
    for comp in re.split(r"[-.]", stem):
        if _STAGE_STEM_TOKEN.fullmatch(comp):
            stem_cand = comp
            break
    return dir_cand, stem_cand


def _cover_block(html_text: str, heading: str, next_headings: list[str]
                 ) -> tuple[str | None, list[str]]:
    """DOCX-native/ODT-track cover-block text+URL extraction, mirroring the
    approach check_html_cover uses for its own This/Previous/Latest parsing
    (Word front-loads hundreds of KB of styles/xml; the cover starts at
    <body>). This check's own copy is deliberately self-contained rather
    than a module-level extraction shared with check_html_cover: this
    batch's single-AC integration mechanism (helpers+function inserted at
    one marker point, see rebuttals) has no coordinated way to also patch a
    second, independently-owned function's body, and check_html_cover's own
    block parser is a local closure today, not an importable primitive.
    Kept as ONE reusable function within this check (called once per
    heading) rather than tripled, and returns the raw block text alongside
    the URLs so the caller can test for a literal 'N/A' block (adversary
    MAJOR: 'N/A and missing Previous-stage evidence'). Body-tag search is
    case-insensitive (check_html_cover's own literal '<body' search is not;
    this self-contained copy has no reason to inherit that narrow gap)."""
    m0 = re.search(r"<body", html_text, re.I)
    cover = html_text[m0.start() if m0 else 0:][:120000]
    head = re.sub(r"<[^>]+>", " ", cover)
    head = re.sub(r"&nbsp;|&#160;|\s+", " ", head)
    m = re.search(heading, head, re.I)
    if not m:
        return None, []
    seg = head[m.end():]
    cut = len(seg)
    for e in next_headings:
        m2 = re.search(e, seg, re.I)
        if m2:
            cut = min(cut, m2.start())
    seg = seg[:cut]
    return seg, re.findall(r"https?://docs\.oasis-open\.org/[^\s\"<>]+", seg)


def _md_previous_block_text(md_text: str) -> str | None:
    """Raw text of the markdown 'Previous Stage/Version' front-matter block,
    or None if the heading is not found at all. stage_urls_from_md returns
    only the URLs it finds inside a block, never the surrounding text, so a
    literal 'N/A' block cannot be told apart from a missing/malformed one
    through that helper alone; this mirrors its exact heading regex but is
    scoped to just the one heading this check needs the raw text for (not a
    general-purpose refactor of the shared helper -- see rebuttals)."""
    m = re.search(r"^#+ Previous (?:Stage|Version)\b.*?$(.*?)^#+ ",
                  md_text, re.M | re.S | re.I)
    return m.group(1) if m else None

def check_stage_token(md_text: str, html_text: str, stage: str, f: Findings) -> None:
    """AC-FRONTMATTER-07: while the package's own current stage is csd/cnd, a
    Previous-stage cover URI SHOULD carry a matching, non-retired stage token
    (WARN -- it may legitimately be a pre-Naming-Directives-v1.7 legacy URI,
    naming-directives.txt 6.3 Resource Permanence), and a Latest-stage cover
    URI's filename must embed NO stage-abbreviation token at all, matching or
    not (BLOCKER -- naming-directives.txt 6.2 is an absolute prohibition on
    that specific position). This-stage tokens are out of scope: the
    existing BLOCKER-severity front-matter/stage-name/filenames checks
    already guarantee them for any package reaching here."""
    md_text = md_text or ""
    html_text = html_text or ""
    stage = stage or ""
    sm = re.fullmatch(r"([a-z]+)(\d\d)?", stage, re.IGNORECASE)
    doc_stage_token = (sm.group(1) if sm else stage).lower()
    if doc_stage_token not in {"csd", "cnd"}:
        f.observe("stage-token", applicability=f"not applicable (stage '{stage}' is not csd/cnd)")
        return
    if md_text:
        this_urls = stage_urls_from_md(md_text, "This")
        previous_urls = stage_urls_from_md(md_text, "Previous")
        latest_urls = stage_urls_from_md(md_text, "Latest")
        previous_block_text = _md_previous_block_text(md_text)
    else:
        # DOCX-native/ODT track: no markdown front matter to parse; pull the
        # same labelled blocks from the rendered HTML cover.
        _, this_urls = _cover_block(html_text, r"This (version|stage)",
                                     [r"Previous (version|stage)", r"Latest (version|stage)",
                                      r"Technical Committee"])
        previous_block_text, previous_urls = _cover_block(
            html_text, r"Previous (version|stage)",
            [r"Latest (version|stage)", r"Technical Committee"])
        _, latest_urls = _cover_block(html_text, r"Latest (version|stage)",
                                       [r"Technical Committee", r"Chairs?\b"])
    if not this_urls:
        f.observe("stage-token", applicability="This-stage block missing/empty; deferred "
                  "to the existing front-matter BLOCKER, not independently re-checked here")
        return
    previous_is_na = bool(
        previous_block_text is not None
        and re.sub(r"\s+", " ", previous_block_text).strip().casefold() == "n/a")
    if previous_block_text is None:
        previous_status = "(no Previous-stage block found)"
    elif previous_is_na:
        previous_status = "N/A (first instance)"
    elif previous_urls:
        previous_status = ", ".join(sorted(set(previous_urls)))
    else:
        previous_status = "(block present, no URLs found)"
    f.observe("stage-token", doc_stage_token=doc_stage_token,
              this_stage_block="present (not independently evaluated)",
              previous_stage_status=previous_status,
              latest_stage_urls=latest_urls or "(none)")
    fired = False
    if not previous_is_na:
        for raw_u in previous_urls:
            u = _clean_url(raw_u)
            dir_cand, stem_cand = _extract_stage_tokens(u)
            for candidate, position in ((dir_cand, "directory segment"), (stem_cand, "filename stem")):
                if not candidate:
                    continue
                bare = _bare_stage_token(candidate)
                if bare in RETIRED_STAGE_TOKENS:
                    fired = True
                    f.add(WARN, "stage-token",
                          f"Previous-stage URL carries a retired stage token '{candidate}' "
                          f"in its {position}: {u}. handbook-PublicReviews.txt: "
                          f"'Do not use csprd or cnprd in filenames, URIs, or cover pages' "
                          f"(the retired set also includes cos/csdpr/cndpr, per handbook-"
                          f"Naming.txt's retirement list and the 'stage-name' check's own "
                          f"vocabulary). Previous-stage may legitimately retain a pre-2 "
                          f"January 2024 legacy token if the linked document was published "
                          f"before Naming Directives v1.7 took effect (naming-directives.txt "
                          f"6.3 Resource Permanence) -- verify the linked document's original "
                          f"publication date before treating this as an error.")
                elif bare != doc_stage_token:
                    fired = True
                    f.add(WARN, "stage-token",
                          f"Previous-stage URL's {position} carries stage token '{candidate}' "
                          f"(expected '{doc_stage_token}'): {u}. handbook-PublicReviews.txt: "
                          f"the three cover page URIs 'should all reflect the "
                          f"{doc_stage_token} stage abbreviation.'")
    for raw_u in latest_urls:
        u = _clean_url(raw_u)
        _dir_cand, stem_cand = _extract_stage_tokens(u)
        if stem_cand:
            fired = True
            f.add(BLOCKER, "stage-token",
                  f"Latest-stage URL's filename embeds a stage-abbreviation token "
                  f"'{stem_cand}': {u}. naming-directives.txt 6.2: the Latest-stage URI "
                  f"'does not contain the path component [stage-abbrev][revisionNumber] "
                  f"or stage identifier in the filename', regardless of whether the "
                  f"embedded token matches the current stage.")
    if not fired:
        f.observe("stage-token", result="PASS -- Previous-stage tokens match/legacy-clean "
                  "or N/A, Latest-stage filenames carry no stage token")


# ===== AC-FRONTMATTER-10 (title-version) =====
VERSION_TOKEN_RE = re.compile(
    r"(?P<word>version)\s+(?P<num>[0-9]+(?:\.[0-9]+)*)", re.IGNORECASE)

TITLE_STANDARDS_TRACK_STAGES = {"csd", "cs", "os", "errata"}
TITLE_NON_STANDARDS_TRACK_STAGES = {"cnd", "cn"}


def _version_token_matches(text: str) -> list:
    """Non-overlapping 'version <n>' matches where 'version' is not itself
    preceded by an alphabetic character. Uses str.isalpha() (Unicode-aware)
    rather than a regex lookbehind restricted to [A-Za-z], so a non-ASCII
    letter glued directly onto 'version' (e.g. an accented word) is still
    excluded -- the same guard the ASCII case already needs against
    'Conversion 1.2' / 'Diversion 2.0' spuriously matching '-version 1.2'."""
    out = []
    for m in VERSION_TOKEN_RE.finditer(text):
        before = text[:m.start("word")]
        if before and before[-1].isalpha():
            continue
        out.append(m)
    return out


def _resolve_html_title(html_text: str) -> tuple[str, bool]:
    """The <title> element text and whether it names exactly one matching
    <h1> (mirrors check_html's html-residue duplicate-title detection, so a
    dependent check can defer to that resolution instead of independently
    guessing 'the first' H1 when the upstream check has not passed). The
    <h1> comparison intentionally does NOT decode entities beyond tag
    stripping -- it mirrors check_html's own norm() verbatim so the two
    stay in lockstep; only the extracted <title> text (used for Version-
    token matching below) gets whitespace-entity normalization."""
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    if not m:
        return "", False
    title = re.sub(r"&nbsp;|&#160;", " ", m.group(1))
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        return "", False
    flat = re.sub(r"\s+", " ", html_text)
    h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", flat, re.I | re.S)
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip().lower()
    dup = sum(1 for h in h1s if norm(h) == title.lower())
    return title, dup == 1


def _docx_cover_title(html_text: str) -> str:
    """The DOCX-native cover title: the first Title-styled (Word 'MsoTitle')
    paragraph in the cover window, matched by class TOKEN (not a literal
    class-attribute prefix) so a converted DOCX carrying multiple classes
    (e.g. class="foo MsoTitle") still resolves; absent that style, the
    first non-empty cover paragraph that is not the OASIS-logo image
    anchor (position order is deterministic; no font-size heuristic
    needed). The 120000-char cover window mirrors check_html_cover's own
    established scoping for this exact 'parse the rendered Word cover'
    problem -- Word's HTML export carries no reliable, already-consumed
    page-break marker in this codebase, so a true page-1 boundary is not
    available; first document-order match within the cover window is the
    deterministic proxy already in use elsewhere in this file."""
    body_at = html_text.find("<body")
    cover = html_text[body_at if body_at >= 0 else 0:][:120000]

    def _text(inner: str) -> str:
        t = re.sub(r"<[^>]+>", " ", inner)
        t = re.sub(r"&nbsp;|&#160;", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    paras = list(re.finditer(r"<p\b([^>]*)>(.*?)</p>", cover, re.I | re.S))
    for pm in paras:
        if re.search(r'\bclass\s*=\s*["\']?[^"\'>]*\bMsoTitle\b', pm.group(1), re.I):
            return _text(pm.group(2))
    for pm in paras:
        if re.search(r"<img\b", pm.group(2), re.I):
            continue  # OASIS-logo image anchor: excluded from the fallback
        text = _text(pm.group(2))
        if text:
            return text
    return ""

def check_title_version(html_text: str, version: str, stage: str,
                        is_word: bool, f: Findings) -> None:
    """AC-FRONTMATTER-10 (naming-directives.txt 5.1 + Section 7): the
    rendered cover-page title must incorporate the package's own Version
    identifier and, for Standards Track Work Products, must compose it as
    '<name/identifier> Version <number>'. A Working Draft is not a Work
    Product and carries no Naming-Directives-recognized stage abbreviation
    (handbook-WorkingDrafts.txt), so this check does not apply to wd.
    Stage prefix matching is case-insensitive: version/stage always arrive
    as strings from parse_stage() (os.path.basename never returns None),
    matching every other stage/version-consuming check in this file (e.g.
    check_stage_name, check_version_naming), which likewise trust that
    contract rather than re-guard against an input shape that cannot
    reach this call site."""
    stage_l = stage.lower()
    m_stage = re.match(r"[a-z]+", stage_l)
    prefix = m_stage.group(0) if m_stage else stage_l
    if prefix == "wd":
        f.observe("title-version", stage=stage,
                  evaluated="no (Working Draft is not a Work Product)")
        return

    pkg_version = version[1:] if version.startswith("v") else version

    if is_word:
        title_text = _docx_cover_title(html_text) if html_text else ""
        source = "DOCX cover title paragraph"
    else:
        title_text, unique = _resolve_html_title(html_text) if html_text else ("", False)
        source = "HTML <title>/<h1>"
        if title_text and not unique:
            f.observe("title-version", stage=stage, title_source=source,
                      title_text=title_text, evaluated="no")
            f.add(INFO, "title-version",
                  "Not evaluated: blocked by an upstream html-residue defect "
                  "(the document title does not resolve to exactly one "
                  "matching <h1>).")
            return

    if not title_text:
        f.observe("title-version", stage=stage, title_source=source,
                  title_text="(absent)", evaluated="no")
        f.add(INFO, "title-version",
              "Not evaluated: no cover-page title text could be resolved.")
        return

    if prefix in TITLE_STANDARDS_TRACK_STAGES:
        track = "standards"
    elif prefix in TITLE_NON_STANDARDS_TRACK_STAGES:
        track = "non-standards"
    else:
        track = "unresolved"

    matches = _version_token_matches(title_text)
    f.observe("title-version", stage=stage, track=track, pkg_version=pkg_version,
              title_source=source, title_text=title_text,
              version_tokens_found=len(matches))
    if not matches:
        f.add(BLOCKER, "title-version",
              f"Title does not incorporate a Version identifier: '{title_text}' "
              f"(Naming Directives 5.1: a Version identifier must be "
              f"incorporated into the Work Product title).")
        return

    m = matches[-1]
    num = m.group("num")
    if num != pkg_version:
        f.add(BLOCKER, "title-version",
              f"Title cites a different Version than the package's own Version "
              f"identifier: title has '{num}', package is '{pkg_version}' "
              f"(title: '{title_text}').")

    before = title_text[:m.start("word")]
    punct_ok = before.endswith(" ") and (len(before) < 2 or before[-2].isalnum() or before[-2] == ")")
    word_ok = title_text[m.start("word"):m.end("word")] == "Version"
    after = title_text[m.end("num"):]
    tail_ok = after == "" or re.fullmatch(r"\.\s*Part\s+\d+:\s+.+", after) is not None
    if not (punct_ok and word_ok and tail_ok):
        comp_sev = BLOCKER if track == "standards" else WARN
        note = (
            " Section 7 permits a punctuation deviation only 'in consultation "
            "with Project Administration' -- confirm no such consultation is "
            "on record before treating this as a hard defect."
            if track == "standards" else
            " Non-Standards Track (Section 7: 'should be followed ... unless "
            "there are reasonable grounds for alternate constructions')."
            if track == "non-standards" else
            f" Track for stage token '{prefix}' is unresolved -- no corpus "
            "citation establishes Standards vs Non-Standards Track for this "
            "token; escalate for classification before treating this as "
            "blocking."
        )
        f.add(comp_sev, "title-version",
              f"Title's Version composition does not follow the required "
              f"'<name> Version <number>' pattern (title: '{title_text}')." + note)


# ===== AC-FRONTMATTER-12 (title-oasis-prefix) =====
import html


def _classify_work_product_track(stage: str):
    """Standards Track vs Non-Standards Track, from the stage directory's
    prefix (Naming Directives v1.7 stage abbreviations; the same prefix
    check_stage_name already parses). cnd/cn (Committee Note family) and
    pn/pnd (Project Note family, the OASIS Open Projects Non-Standards Track
    equivalent) are Non-Standards Track; csd/cs/os/ps/psd/errata (Committee/
    Project Specification and Standard family) are Standards Track. Returns
    (track, confident) -- confident is False for 'wd' (Working Draft exists
    on both tracks per the Handbook and cannot be classified from the stage
    token alone) and for any unrecognized token (check_stage_name's own
    BLOCKER to fix, not this check's to guess past). Both ambiguous cases
    still default to Standards Track, the stricter tier -- defensible
    because this check never asserts a confirmed violation, only flags the
    pattern for human confirmation (naming-directives.txt s7) -- but
    confident=False makes that default visible in the finding text and
    observed evidence instead of presenting it as equivalent to a confirmed
    csd/cs/os/ps/psd/errata classification (adversary MAJOR: 'severity /
    track gating')."""
    m = re.fullmatch(r"([a-z]+)(\d\d)?", stage or "")
    prefix = m.group(1) if m else (stage or "")
    if prefix in {"cnd", "cn", "pn", "pnd"}:
        return "non-standards", True
    if prefix in {"csd", "cs", "os", "ps", "psd", "errata"}:
        return "standards", True
    return "standards", False


# AC-FRONTMATTER-12 (naming-directives.txt s7): "Preferably, a title should
# not begin with the name 'OASIS' except on the recommendation of Project
# Administration for special cases." Case-insensitive, word-boundary,
# start-of-string only -- matches "OASIS ..." not a title that merely
# contains OASIS mid-string, and not a word-glued leading token like
# "Oasismethodology". A leading run of common quote/punctuation characters
# and non-breaking/zero-width whitespace is stripped first.
_TITLE_STRIP_CHARS = (
    " \t\n\r\v\f ​‌‍﻿"
    "\"'‘’“”([-–—"
)
_TITLE_OASIS_PREFIX = re.compile(r"^oasis\b", re.IGNORECASE)


def _norm_h1_text(raw: str) -> str:
    """Strip tags, HTML-unescape entities, collapse whitespace. The tag-strip
    and whitespace-collapse mirror check_html's own D1 dup-count norm()
    exactly; the added html.unescape() pass closes a real mismatch: <title>
    text arrives already entity-decoded (HTMLParser(convert_charrefs=True)),
    but a raw regex-extracted <h1> does not, so an entity-bearing title like
    'OASIS Foo &amp; Bar' would silently fail to text-match its own decoded
    <title> counterpart 'OASIS Foo & Bar' without this (adversary MAJOR:
    'false negatives / HTML text extraction')."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", raw))).strip()


def _h1_title_match_info(html_text: str, title: str):
    """The one shared <h1>-vs-<title> classification both check_html's D1
    lint and this check need -- factored out so the two checks' notion of
    'the H1(s) matching the title' cannot silently drift apart on a future
    edit to one but not the other (verify.json MAJOR: 'helper-reuse';
    adversary MINOR: 'idiom / duplicated logic'). check_html's own D1 finding
    only fires when 2+ H1s exactly match <title> (dup > 1); it is silent on
    the 0-match case, which is NOT the same as 'no ambiguity' -- a template
    that appends a trailing suffix to <title> alone (e.g. '<Real Title> |
    OASIS Open', the exact convention naming-directives.txt's own
    false-positive-risk list names for the opposite direction) produces
    exactly this silent 0-match state even though the document's sole <h1>
    is perfectly identifiable. Returns (kind, h1_text_or_None,
    exact_match_count, total_h1_count):
      - 'exact': exactly 1 <h1> text-matches <title> verbatim (D1's own PASS
        case) -- the strong primary source.
      - 'singular-related-fallback': 0 exact matches, but exactly 1 <h1>
        exists in the document AND it is a normalized prefix of <title> or
        vice versa (the trailing-suffix-on-<title>-only pattern above) --
        used as a lower-confidence source rather than silently skipping a
        genuine violation (adversary BLOCKER: 'D1 premise / false
        negatives').
      - 'singular-unrelated': 0 exact matches, exactly 1 <h1>, but it shares
        no prefix relationship with <title> at all (e.g. a stray heading
        totally unrelated to the document title) -- still SKIP; guessing a
        fallback here would be exactly the "unjustified <title>-vs-H1
        preference rule" the spec's own algorithm step 3 forbids.
      - 'none': 0 <h1> elements in the document at all.
      - 'ambiguous': 2+ exact matches (D1's own dup>1 BLOCKER state), or 0
        exact matches with 2+ total H1s and no singular fallback available
        -- genuinely undecidable either way; no fallback preference guessed.
    """
    flat = re.sub(r"\s+", " ", html_text)
    h1s_raw = re.findall(r"<h1\b[^>]*>(.*?)</h1>", flat, re.I | re.S)
    h1s = [_norm_h1_text(h) for h in h1s_raw]
    title_norm = _norm_h1_text(title)
    tl = title_norm.lower()
    exact = [h for h in h1s if h.lower() == tl]
    if len(exact) == 1:
        return "exact", exact[0], 1, len(h1s)
    if len(exact) >= 2:
        return "ambiguous", None, len(exact), len(h1s)
    # len(exact) == 0
    if len(h1s) == 0:
        return "none", None, 0, 0
    if len(h1s) == 1:
        h1l = h1s[0].lower()
        if h1l and tl and (tl.startswith(h1l) or h1l.startswith(tl)):
            return "singular-related-fallback", h1s[0], 0, 1
        return "singular-unrelated", None, 0, 1
    return "ambiguous", None, 0, len(h1s)

def check_frontmatter_title_oasis_prefix(html_text: str, stage: str, f: Findings) -> None:
    """AC-FRONTMATTER-12: the Work Product title -- approximated as the
    <h1> element identified by _h1_title_match_info's 0/1/2+ classification
    against the rendered <title> text (the same classification check_html's
    D1 lint performs for its own duplicate-title finding, plus a
    singular-unmatched-<h1> fallback D1 itself does not need for its own
    narrower purpose) -- should not begin with the word 'OASIS'.
    naming-directives.txt s7: 'Preferably, a title should not begin with the
    name "OASIS" except on the recommendation of Project Administration for
    special cases.' Section 7's lead sentence track-scopes every rule in the
    section: must-observe for Standards Track (BLOCKER here), should-follow
    with an additional 'reasonable grounds for an alternate construction'
    escape valve for Non-Standards Track (WARN here). pub-check has no
    visibility into a Project Administration recommendation on record, so a
    match is always flagged for human confirmation, never asserted as a
    confirmed violation.

    html_text is the single output every track already renders to (Word
    HTML export on the DOCX-native track, pandoc HTML on the markdown
    track) -- registry.json's own html-residue '<h1> elements' check (D1)
    already applies "both" tracks against this same <h1> regex on this same
    html_text, so DOCX-native packages are covered by the identical
    extraction the shipped D1 lint already trusts for that track, not a new
    gap (see rebuttals: DOCX-native <h1> extraction). If neither an exact
    nor a singular-related-fallback <h1> can be identified, this check
    cannot reliably identify the title and SKIPs its content determination
    rather than guessing."""
    if not html_text:
        f.observe("title-oasis-prefix",
                  title_source="(no HTML rendering; see 'Missing delivery format(s)')")
        return
    p = _AnchorParser()
    p.feed(html_text)
    title = " ".join(p.title.split())
    if not title:
        f.observe("title-oasis-prefix", title_source="(no <title> element in the HTML)")
        return
    kind, raw_h1, exact_n, total_h1 = _h1_title_match_info(html_text, title)
    if kind in ("none", "ambiguous", "singular-unrelated"):
        if kind == "none":
            detail = "0 <h1> elements found in the rendered HTML"
        elif kind == "singular-unrelated":
            detail = ("the document's sole <h1> shares no prefix relationship with the "
                       "<title> text -- cannot reliably identify the Work Product title")
        else:
            detail = (f"{exact_n} <h1> element(s) exactly matching the <title> text out of "
                       f"{total_h1} <h1> element(s) total (need exactly 1 matching, or "
                       f"exactly 1 <h1> total as a fallback)")
        f.observe("title-oasis-prefix",
                  title_source=f"not applicable -- html-residue D1 classification is "
                  f"'{kind}': {detail}")
        return
    raw_title = raw_h1
    normalized = raw_title.lstrip(_TITLE_STRIP_CHARS)
    track, confident = _classify_work_product_track(stage)
    confidence_note = (
        "" if confident else
        " (stage prefix alone does not distinguish Standards from Non-Standards Track -- "
        "e.g. 'wd' is used on both -- defaulted to the stricter Standards Track tier for "
        "this flag)")
    fallback_note = (
        "" if kind == "exact" else
        " (lower confidence: no <h1> exactly matched the rendered <title> text -- likely a "
        "template/branding suffix decorating <title> alone -- so the document's sole <h1> "
        "is used as the title source instead)")
    f.observe("title-oasis-prefix", title_source=raw_title, track=track,
              track_confidence="confirmed" if confident else "defaulted (ambiguous stage prefix)",
              title_match=kind)
    if _TITLE_OASIS_PREFIX.match(normalized):
        sev = BLOCKER if track == "standards" else WARN
        escape_valves = (
            "a Project Administration recommendation on record for this title"
            if track == "standards" else
            "a Project Administration recommendation on record for this title, "
            "or reasonable grounds for an alternate construction (e.g. marketing "
            "material, presentation-ware)")
        f.add(sev, "title-oasis-prefix",
              f"Work Product title begins with 'OASIS': '{raw_title}'{fallback_note}. "
              f"Naming Directives v1.7 s7: a title should not begin with the "
              f"name \"OASIS\" except on the recommendation of Project Administration for "
              f"special cases. pub-check cannot confirm or deny {escape_valves}; a human "
              f"reviewer should confirm before treating this as a defect.{confidence_note}")


# ===== AC-FRONTMATTER-18 (authors) =====
# AC-FRONTMATTER-18 (TC Handbook: Technical Reports / Glossary / Work Product
# Lifecycle): a Technical Report or Technical Report Draft names one or more
# Authors on its cover page -- the trait the Handbook uses to distinguish a
# TR from a Committee Note's Editors-only listing.
AUTHORS_HEADING_RE = re.compile(r"^(#+)\s*Authors?\b.*$", re.M | re.I)
AUTHORS_BYLINE_RE = re.compile(
    r"\bby\s+([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+)*"
    r"(?:,?\s+(?:and|&)\s+[A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+)*)*)")
AUTHORS_BYLINE_PLACEHOLDER_RE = re.compile(
    r"\bby\s+(tbd|n/a|none|will\s+be\s+filled\s+in)\b\.?", re.I)
AUTHORS_BLOCKER_PLACEHOLDERS = {"tbd", "n/a", "none"}
AUTHORS_WARN_PLACEHOLDER = "will be filled in"
AUTHORS_WP_TYPES = {"technical report": "tr", "technical report draft": "trd"}
_LIST_MARKUP_RE = re.compile(
    "^>+\\s*|^(?:[-*+•]\\s+(?:\\[[ xX]\\]\\s+)?|\\(?\\d+[.)]\\s+)")


def _h1_match(md_text: str):
    """The document's first H1 title line, or None. Shared by every helper
    below that needs the title's position, so the '^#\\s+.+$' scan is
    written once, not re-derived per helper."""
    return re.search(r"^#\s+.+$", md_text, re.M)


def _strip_list_markup(line: str) -> str:
    """Strip a leading blockquote marker and/or list marker (bullet, task
    checkbox, ordered '1.'/'1)'/'(1)') so a placeholder line written as
    '- [ ] TBD', '> TBD', or '(1) TBD' normalizes to just 'TBD' -- not
    '[ ] tbd' or '(1) tbd', which would silently escape exact placeholder
    matching and be treated as a real named entry."""
    line = line.strip()
    line = _LIST_MARKUP_RE.sub("", line, count=1)
    return line.strip()


def _normalize_heading_text(label: str) -> str:
    """Markdown-aware cleanup for a cover-adjacent type-label heading's raw
    text: strip HTML tags, Pandoc/header attributes ('{#id .class}'),
    closing ATX hashes, emphasis markers, NBSP and curly-quote noise, then
    collapse whitespace and strip a trailing revision-number token -- so
    '## **Technical Report Draft 01** {#stage}' or a curly-quoted variant
    still normalize to 'technical report draft', matching a plain
    '## Technical Report Draft'."""
    label = re.sub(r"<[^>]+>", "", label)
    label = re.sub(r"\{#[^}]*\}\s*$", "", label)
    label = re.sub(r"#+\s*$", "", label)
    label = label.replace(" ", " ")
    label = re.sub(r"[*_]{1,3}", "", label)
    label = re.sub("[‘’“”]", "", label)
    label = re.sub(r"\s+", " ", label).strip()
    label = label.strip(" .:-–—")
    label = re.sub(r"\s*\d{1,3}\s*$", "", label).strip(" .:-–—")
    return label.lower()


def _cover_type_label(md_text: str) -> str:
    """Normalized work-product-type label: the heading immediately following
    the document's first H1 title (the canonical, title-adjacent cover-page
    type line), never a body-prose occurrence of the phrase. See
    _normalize_heading_text for the markdown-aware normalization applied."""
    h1 = _h1_match(md_text)
    if not h1:
        return ""
    m = re.search(r"^#{1,6}\s+(.+)$", md_text[h1.end():], re.M)
    if not m:
        return ""
    return _normalize_heading_text(m.group(1))


def _title_block(md_text: str) -> str:
    """The cover-page byline scan window: from the start of the document
    through the end of the section immediately following the first H1 title
    (the type-label heading, plus any text under it up to the next
    heading). Wide enough to catch a byline on the title line itself, on
    the line directly under the title, or under the type-label heading --
    without reaching into the later Editors/Abstract front-matter
    sections."""
    h1 = _h1_match(md_text)
    if not h1:
        return md_text
    rest = md_text[h1.end():]
    type_m = re.search(r"^#{1,6}\s+.+$", rest, re.M)
    if not type_m:
        return md_text[:h1.end()]
    after_type = rest[type_m.end():]
    nxt = re.search(r"^#{1,6}\s", after_type, re.M)
    end = h1.end() + type_m.end() + (nxt.start() if nxt else len(after_type))
    return md_text[:end]


def _front_matter_window(md_text: str) -> str:
    """The cover/front-matter portion of the document: from the start
    through the end of the Abstract section (the last required
    TEMPLATE_SECTIONS heading in the registry's own front-matter template),
    so an Authors heading match cannot be satisfied by an unrelated
    body/appendix section reusing the word 'Authors'. Falls back to the
    whole document when no Abstract heading is present (a missing Abstract
    is separately BLOCKER via check_template, not this check's concern)."""
    m = re.search(r"^#+\s+Abstract\b", md_text, re.M | re.I)
    if not m:
        return md_text
    nxt = re.search(r"^#{1,6}\s", md_text[m.end():], re.M)
    return md_text[:m.end() + (nxt.start() if nxt else len(md_text) - m.end())]


def _authors_block(md_text: str):
    """Text between an Authors/Author(s) heading and the next heading of
    equal-or-higher level, mirroring the registry's own required '## Editors'
    heading precedent (check='template'). Scoped to the front-matter window
    (through Abstract) so a later body/appendix section cannot masquerade as
    the cover-page Authors record. None if no such heading exists there."""
    window = _front_matter_window(md_text)
    m = AUTHORS_HEADING_RE.search(window)
    if not m:
        return None
    level = len(m.group(1))
    rest = window[m.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    return rest[:nxt.start()] if nxt else rest

def check_authors(md_text: str, is_word: bool, is_odt: bool, f: Findings) -> None:
    """AC-FRONTMATTER-18: a Technical Report/Technical Report Draft must name
    one or more Authors on its cover page (a dedicated Authors heading,
    mirroring the registry's own mandatory Editors heading, or a title-block
    byline) -- the trait the TC Handbook uses to distinguish a TR from a
    Committee Note's Editors-only listing (handbook-TechnicalReports.txt,
    handbook-Glossary.txt, handbook-WorkProductLifecycle.txt). Out of scope
    for CN/CND and every Standards Track package. Docx-native TR/TRD covers
    have no established Authors convention in the corpus, so this check
    applies to the md track only (applies='md'); is_word short-circuits
    before any classification regardless of what md_text happens to hold, so
    a docx-native package can never be auto-flagged for this check even if a
    converted/extracted markdown proxy is passed alongside it. Every other
    no-markdown-source track (ODT-native, HTML-only) is likewise a
    deliberate no-op with its own observed evidence, never silently
    unrecorded and never auto-flagged for a check scoped to the md track."""
    if is_word or not md_text:
        if is_word:
            f.observe("authors", track="docx-native",
                      note="Authors convention not established for docx-native "
                           "covers; not evaluated here, route to manual review")
        elif is_odt:
            f.observe("authors", track="odt-native",
                      note="no markdown source; this check applies to the md "
                           "track only, not evaluated here")
        else:
            f.observe("authors", track="no-markdown-source",
                      note="no markdown source; this check applies to the md "
                           "track only, not evaluated here")
        return
    text = strip_code_blocks(md_text, "md")
    wp_type = _cover_type_label(text)
    if wp_type not in AUTHORS_WP_TYPES:
        f.observe("authors", work_product_type=wp_type or "(not TR/TRD)")
        return
    is_trd = AUTHORS_WP_TYPES[wp_type] == "trd"
    block = _authors_block(text)
    source = "Authors heading"
    if block is None:
        tb = _title_block(text)
        ph = AUTHORS_BYLINE_PLACEHOLDER_RE.search(tb)
        if ph:
            block = re.sub(r"\s+", " ", ph.group(1)).strip()
        else:
            m = AUTHORS_BYLINE_RE.search(tb)
            if not m:
                f.observe("authors", work_product_type=wp_type, authors_source="(none found)")
                f.add(BLOCKER, "authors",
                      "No Authors section or byline found for Technical Report/Technical "
                      "Report Draft: the TC Handbook requires one or more named Authors "
                      "recorded on the cover page (this distinguishes a Technical Report "
                      "from a Committee Note, which lists editors).")
                return
            block = m.group(1)
        source = "title-block byline"
    names, blocker_placeholder, warn_placeholder = [], False, False
    for raw in block.splitlines():
        line = _strip_list_markup(raw)
        if not line:
            continue
        norm = line.strip(" .").lower()
        if norm in AUTHORS_BLOCKER_PLACEHOLDERS:
            blocker_placeholder = True
        elif norm == AUTHORS_WARN_PLACEHOLDER:
            warn_placeholder = True
        else:
            names.append(line)
    f.observe("authors", work_product_type=wp_type, authors_source=source,
              authors_found=names or "(none)")
    if names:
        return
    if blocker_placeholder or not warn_placeholder:
        f.add(BLOCKER, "authors",
              "Authors section is empty or placeholder-only for a Technical Report/"
              "Technical Report Draft: one or more named Authors must be recorded "
              "on the cover page.")
    elif is_trd:
        f.add(WARN, "authors",
              "Authors section contains an unresolved 'will be filled in' placeholder "
              "-- tolerated for a Technical Report Draft but must be resolved before "
              "the final Technical Report Full Majority Vote.")
    else:
        f.add(BLOCKER, "authors",
              "Authors section still reads 'will be filled in' on an approved "
              "Technical Report: the early-stage placeholder exemption does not "
              "survive Full Majority Vote approval.")


# ===== AC-NAMING-07 (name-chars) =====
NAME_CHARS_STRICT_ALLOWED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-")
NAME_CHARS_BASE_ALLOWED = NAME_CHARS_STRICT_ALLOWED | frozenset("_")
NAME_CHARS_PART_DIR = re.compile(r"^part\d+[-_].+$")


def _name_chars_offenders(name: str, allowed: frozenset) -> str:
    """Characters in `name` outside `allowed`, de-duplicated, first-seen
    order (used both to build the human-readable offender list and to
    detect the single-underscore-only case)."""
    out = []
    for ch in name:
        if ch not in allowed and ch not in out:
            out.append(ch)
    return "".join(out)

def check_name_chars(stage_dir: str, version: str, stage: str, stem: str,
                     f: Findings) -> None:
    """Naming Directives v1.7 s3 (Name Characters for Files and
    Directories): every filename/directory name in the package uses only
    the sixty-four permitted characters {A-Za-z0-9} + PERIOD + HYPHEN;
    UNDERSCORE is tolerated only outside document-cover-page-URI-bearing
    ('identifying') names, and even there only as a non-blocking WARN --
    the tool cannot verify the corpus's 'unavoidably application-generated'
    condition, so it surfaces the fact rather than asserting compliance or
    violation. Identifying names -- the stage directory, the version
    directory, the stage-root delivery file(s) sharing the package's
    established basename, and any Multi-Part partN-name/ directory plus
    the file(s) directly inside it -- are held to the strict allowlist
    with zero underscore tolerance: an UNDERSCORE 'must never be used in a
    filename or directory name that is used in a document URI.' An empty
    identifying name (a degenerate/missing token) is a BLOCKER on the same
    STRICT test, not a silent pass -- matching how check_stage_name's and
    check_version_naming's own fullmatch patterns already reject an empty
    stage/version token organically via their '+' quantifiers. stage_dir/
    stage/version are trusted as run()'s parse_stage()-derived contract
    (stage_dir already validated as a real, readable directory by main()
    before run() is ever called; stage/version are never None, worst case
    an empty string for a degenerate path), exactly like every sibling
    check in this file (check_hygiene, check_stage_name, check_version_naming)
    that consumes the same values with no defensive re-validation of its
    own."""

    def identifying(name: str, where: str) -> None:
        if not name:
            f.add(BLOCKER, "name-chars",
                  f"Empty {where}: Naming Directives v1.7 s3's sixty-four-"
                  f"character allowlist requires at least one character -- "
                  f"an empty name cannot satisfy it.")
            return
        bad = _name_chars_offenders(name, NAME_CHARS_STRICT_ALLOWED)
        if not bad:
            return
        if bad == "_":
            f.add(BLOCKER, "name-chars",
                  f"Underscore in {where} '{name}': Naming Directives v1.7 "
                  f"s3 -- an UNDERSCORE 'must never be used in a filename or "
                  f"directory name that is used in a document URI'; use "
                  f"HYPHEN instead.")
        else:
            f.add(BLOCKER, "name-chars",
                  f"Forbidden character(s) '{bad}' in {where} '{name}': "
                  f"Naming Directives v1.7 s3 requires filenames and "
                  f"directory names use only alphanumerics, PERIOD, and "
                  f"HYPHEN (the sixty-four permitted characters) -- no "
                  f"exception applies to an identifying package name.")

    def supporting(rel: str, name: str) -> None:
        bad = _name_chars_offenders(name, NAME_CHARS_BASE_ALLOWED)
        if bad:
            f.add(BLOCKER, "name-chars",
                  f"Forbidden character(s) '{bad}' in supporting package "
                  f"name '{rel}': Naming Directives v1.7 s3 -- TCs must use "
                  f"only alphanumerics, PERIOD, and HYPHEN, plus UNDERSCORE "
                  f"where an application unavoidably generates it; no other "
                  f"character is permitted anywhere in the package.")
        # Underscore in a supporting (non-URI) filename is permitted by the
        # Handbook; the no-underscore rule applies only to document URIs,
        # which the uri-chars check enforces.

    # steps 2 + 4: stage + version directory names, pulled from the package
    # path independent of the downward walk (the version dir is the PARENT
    # of the stage dir and can never be reached by walking down from it).
    identifying(stage, "the stage directory name")
    identifying(version, "the version directory name")

    # step 3: junk-dir-aware recursive walk of everything at/below the
    # stage root; junk-files already BLOCKERs a package carrying one of
    # these, so a hit here is a coverage caveat, not a silent exclusion.
    junk_hit: set = set()
    part_dirs: set = set()
    scanned = 0
    stage_norm = os.path.normpath(stage_dir)
    for root, dirs, files in os.walk(stage_dir):
        for d in list(dirs):
            if d in JUNK_DIRS:
                junk_hit.add(os.path.relpath(os.path.join(root, d), stage_dir))
                dirs.remove(d)
        depth0 = os.path.normpath(root) == stage_norm
        root_rel = os.path.relpath(root, stage_dir)
        in_part_dir = root_rel in part_dirs
        for d in dirs:
            scanned += 1
            rel = os.path.relpath(os.path.join(root, d), stage_dir)
            if depth0 and NAME_CHARS_PART_DIR.fullmatch(d):
                part_dirs.add(rel)
                identifying(d, "a Multi-Part directory name")
            else:
                supporting(rel, d)
        for name in files:
            scanned += 1
            rel = os.path.relpath(os.path.join(root, name), stage_dir)
            if depth0 and stem and os.path.splitext(name)[0] == stem:
                identifying(name, "a delivery item filename")
            elif in_part_dir:
                identifying(name, "a Multi-Part delivery item filename")
            else:
                supporting(rel, name)

    f.observe("name-chars", names_scanned=scanned + 2,
              identifying_stage=stage, identifying_version=version,
              multi_part_dirs=sorted(part_dirs) or "(none)",
              junk_dirs_skipped=sorted(junk_hit) or "(none)")
    if junk_hit:
        f.add(INFO, "name-chars",
              f"Character scan suppressed inside {', '.join(sorted(junk_hit))}: "
              f"resolve the junk-files finding first, then re-run for full "
              f"coverage.")


# ===== AC-NAMING-16 (extension-count) =====
# AC-NAMING-16 helpers (Naming Directives v1.7 s4/s5.2/s9): a filename
# identifying a specific published instance of a Work Product must carry
# exactly one file extension (or one blessed multi-part compound); every
# other package file gets the same two-pattern check as a non-blocking
# advisory (s4's Applicability clause: non-identification-pattern filenames
# are "generally subject to no special rules").
EXTENSION_BLESSED_COMPOUNDS = frozenset({"tar.gz", "tar.bz2", "tar.xz"})

# Section 9's literal, hardcoded exception set -- no runtime allowlist.
EXTENSIONLESS_RECOGNIZED = frozenset({"CATALOG", "catalog", "README", "ChangeLog"})

# Disclosed, non-exhaustive known-extension-token vocabulary (a pattern-match
# advisory, not an IANA-derived classification) used only for Tier B's
# heuristic double-extension check.
EXTENSION_KNOWN_TOKENS = frozenset({
    "html", "htm", "xml", "xsd", "wsdl", "json", "css", "js", "pdf", "doc",
    "docx", "odt", "txt", "csv", "zip", "png", "jpg", "jpeg", "gif", "svg",
    "rtf", "md", "xlsx", "xls", "ppt", "pptx", "epub", "rng", "ttl", "yaml",
    "yml", "tar", "gz", "bz2", "xz",
})

def check_extension_count(stage_dir: str, items: dict[str, str], stem: str,
                          stage: str, f: Findings) -> None:
    """AC-NAMING-16: TIER A (identification-pattern filenames -- the
    stage-directory-root delivery items sharing the package's established
    document-identifier stem, one per shipped format) must carry exactly
    one file extension (or one blessed multi-part compound: tar.gz/
    tar.bz2/tar.xz), tested structurally by subtracting the already-known
    stem 'filenames' computed from the front of the basename -- never by
    guessing at dot-segments, so version-embedded dots inside the stem
    (v1.2.1) can never misfire. A basename is only subtracted against the
    stem when it shares a clean extension boundary (basename == stem, or
    basename starts with stem + '.'); a basename that merely has the stem
    as a character PREFIX (e.g. a stray '-redline' suffix before its own
    extension) is left to the 'filenames' check's own basename-shape tests,
    never misreported here as a missing extension. Naming Directives v1.7
    s4: 'A single file (name) extension must be used in each filename
    except for a recognized set of extensionless filenames in common
    use.' Severity is BLOCKER, except at wd stage where it is capped to
    WARN (s5.2's Note: unpublished drafts 'may use any file naming pattern
    preferred by the TC', so the document-identifier grammar this test
    depends on is not yet mandatory); the wd-stage token match is
    case-folded so 'WD01'/'Wd01' are recognized the same as 'wd01'.

    A blessed multi-part compound (tar.gz/tar.bz2/tar.xz) is only accepted
    when it is the WHOLE remaining suffix (exactly two non-empty
    dot-segments) -- an extra segment ahead of a blessed compound (e.g.
    '.html.tar.gz') still carries more than one extension. Dot-segments
    are never silently dropped for being empty, so a malformed doubled or
    trailing dot ('stem..html', 'stem.html.') is flagged as carrying more
    than one extension rather than passing as a clean single extension.

    TIER B (every other file in the package tree -- schemas, images,
    WSDLs, XML/JSON instances, manifest-style files) is checked for the
    same two patterns but reported only as a non-blocking WARN advisory,
    never BLOCKER: s4's Applicability clause states non-identification-
    pattern Work Product filenames are 'generally subject to no special
    rules' beyond name-character conformance, so a MUST-strength gate
    cannot be defended against this population. Files already claimed by
    the 'junk-files' check (forbidden names/suffixes AND junk directories
    such as .git/__MACOSX/node_modules), and dotfiles, are excluded so the
    two checks stay non-overlapping. Delivery-item exclusion is compared
    on absolute, normalized paths so a relative-vs-absolute `stage_dir`
    cannot cause a Tier A file to be double-scanned under Tier B.

    Disclosed, accepted false negative (Tier B): a dotted-but-effectively-
    extensionless ancillary filename whose dot-segments are all version
    tokens rather than a real extension (e.g. a Multi-Part or public-
    review-metadata-style name with embedded 'vN.N' dots but no formal
    stem-derivation procedure wired into this check yet, per the spec's
    open_questions) is not flagged by either Tier B branch: it has a dot
    (so the zero-dot exceptionless branch does not apply) and its
    penultimate segment is not a known extension token (so the
    lookalike-extension heuristic does not fire either). This is a
    documented, non-blocking gap consistent with the spec's own disclosed
    false_negative_risks for this population, not a silent oversight;
    inventing a bespoke heuristic for it would trade this gap for a new,
    unbounded false-positive surface on legitimate multi-dot ancillary
    names.

    Inputs are guarded defensively (never crash the run on a malformed
    call): a missing/None `items` is treated as empty, a non-string/empty
    item path is skipped, and Tier B's walk is skipped (with a
    zero-count observation) when `stage_dir` is falsy or not a real
    directory.
    """
    _stage_norm = (stage or "").lower()
    m = re.fullmatch(r"([a-z]+)(\d\d)?", _stage_norm)
    prefix = m.group(1) if m else _stage_norm
    sev_a = WARN if prefix == "wd" else BLOCKER

    # ---- Tier A: the already-known, cross-format-validated delivery stem
    tier_a_checked = []
    for path in (items or {}).values():
        if not isinstance(path, str) or not path:
            continue
        basename = os.path.basename(path)
        if not stem or not (basename == stem or basename.startswith(stem + ".")):
            # basename doesn't share the established stem at a clean
            # extension boundary: the 'filenames' check's own basename-shape
            # tests own that defect (e.g. a stray '-redline' suffix between
            # the stem and the file's own extension).
            continue
        tier_a_checked.append(basename)
        remainder = basename[len(stem):]
        segs = remainder[1:].split(".") if remainder.startswith(".") else []
        if not segs or segs == [""]:
            f.add(sev_a, "extension-count",
                  f"Delivery file '{basename}' has no file extension after the "
                  f"document-identifier stem '{stem}'. Naming Directives v1.7 s4 requires "
                  f"a single file extension on every identification-pattern filename.")
        elif len(segs) > 1:
            compound = ".".join(segs[-2:]).lower()
            if not (len(segs) == 2 and all(segs) and compound in EXTENSION_BLESSED_COMPOUNDS):
                f.add(sev_a, "extension-count",
                      f"Delivery file '{basename}' carries more than one file extension "
                      f"after the stem '{stem}': trailing segments '.{'.'.join(segs)}'. "
                      f"Naming Directives v1.7 s4 requires exactly one file extension "
                      f"(or a recognized compound: tar.gz/tar.bz2/tar.xz).")

    # ---- Tier B: every other file in the package tree (files only, never
    # directories), excluding junk-files' forbidden names/dirs and dotfiles.
    delivery_paths = {os.path.normpath(os.path.abspath(p))
                      for p in (items or {}).values() if isinstance(p, str) and p}
    tier_b_checked = 0
    tier_b_flagged = []
    if stage_dir and os.path.isdir(stage_dir):
        for root, dirs, files in os.walk(stage_dir):
            for d in list(dirs):
                if d in JUNK_DIRS:
                    dirs.remove(d)
            for name in files:
                p = os.path.join(root, name)
                if os.path.normpath(os.path.abspath(p)) in delivery_paths:
                    continue
                if name in JUNK_NAMES or name.endswith(("~", ".bak", ".orig", ".swp")):
                    continue
                if name.startswith("."):
                    continue
                rel = os.path.relpath(p, stage_dir)
                tier_b_checked += 1
                if "." not in name:
                    if name not in EXTENSIONLESS_RECOGNIZED:
                        tier_b_flagged.append(rel)
                        f.add(WARN, "extension-count",
                              f"Extensionless filename '{rel}' outside the recognized "
                              f"common-use set (CATALOG, catalog, README, ChangeLog per "
                              f"Naming Directives v1.7 s9). Non-blocking: s4's Applicability "
                              f"clause disclaims special rules for most non-identification "
                              f"Work Product files.")
                else:
                    segs = name.split(".")
                    last = segs[-1].lower()
                    second_last = segs[-2].lower() if len(segs) >= 2 else ""
                    compound = f"{second_last}.{last}"
                    if compound in EXTENSION_BLESSED_COMPOUNDS:
                        continue
                    if second_last in EXTENSION_KNOWN_TOKENS:
                        tier_b_flagged.append(rel)
                        f.add(WARN, "extension-count",
                              f"Filename '{rel}' stem ends in '.{second_last}', a token that "
                              f"commonly denotes a file extension elsewhere -- possible "
                              f"leftover extension from format conversion (heuristic pattern "
                              f"match, non-blocking, not a conclusive finding).")

    f.observe("extension-count",
              tier_a_files_checked=tier_a_checked or "(none)",
              tier_a_severity=sev_a,
              tier_b_files_checked=tier_b_checked,
              tier_b_flagged=tier_b_flagged or "(none)")


# ===== AC-NAMING-17 (extension-conformance) =====
EXTENSION_ALLOWLIST = {
    "txt", "md", "html", "htm", "pdf", "doc", "docx", "odt", "ods", "odp",
    "xls", "xlsx", "ppt", "pptx", "rtf", "xml", "json", "epub",
    "zip", "xsd", "rnc", "rng", "sch", "wsdl", "gc", "svg", "png", "jpg",
    "jpeg", "gif", "csv", "yaml", "yml",
}
EXTENSIONLESS_ALLOWLIST = {"CATALOG", "catalog", "README", "ChangeLog"}


def _extension_conformance_candidates(stage_dir: str, stage: str, stem: str) -> tuple[list[str], list[str]]:
    """Candidate filenames for AC-NAMING-17, per Naming Directives Section 4's
    two prescribed-pattern grammars -- both anchored on the package's OWN
    known [WP-abbrev]-[version-id]-[stage] token (`stem`, the same value
    check_filenames already derived and validated upstream in run(), so this
    reuses that grammar-matching logic rather than re-deriving a weaker one):
    (1) root-level files that share that EXACT stem under any extension --
    the required principal cover-page-URI file plus any sibling saved
    alongside it (the only realistic extra-file case per the spec's
    false_positive_risks, e.g. an invented '.wpz' saved next to the real
    .md/.html/.pdf set); and (2) Multi-Part named-part files anywhere in the
    package whose stem is that same `stem` plus '-part<N>-<partName>'
    (partName may itself contain dots -- only the FINAL dot-separated token
    is ever treated as the extension).

    Anchoring both grammars on the real, already-known delivery stem --
    rather than a bare '-<stage>' or '-<stage>-part<N>-...' suffix search
    over the whole tree -- means a coincidentally-named support/example/
    admin file that merely ends in the stage token (e.g.
    'internal-review-notes-csd01.foo', or 'examples/sample-csd01-part1-
    draft.foo') can never be misread as a principal or named-part delivery
    file: it does not share the WP-abbrev/version-id prefix that makes the
    real delivery stem unique, so the equality/prefix test simply does not
    match. If `stem` does not itself end in '-<stage>' (an inconsistency
    check_filenames has already BLOCKERed upstream, or a caller/test passing
    mismatched stage/stem), this function has no reliable base to construct
    either grammar from and returns no candidates rather than guessing."""
    if not stem or not stem.endswith(f"-{stage}"):
        return [], []
    principal: list[str] = []
    try:
        names = sorted(os.listdir(stage_dir))
    except OSError:
        names = []
    for name in names:
        p = os.path.join(stage_dir, name)
        if not os.path.isfile(p):
            continue
        file_stem, dot, _ext = name.rpartition(".")
        if dot and file_stem == stem:
            principal.append(name)
    part_re = re.compile(rf"{re.escape(stem)}-part\d+-.+")
    parts: list[str] = []
    for root, _dirs, files in os.walk(stage_dir):
        for name in sorted(files):
            file_stem, dot, _ext = name.rpartition(".")
            if dot and part_re.fullmatch(file_stem):
                parts.append(os.path.relpath(os.path.join(root, name), stage_dir))
    return principal, sorted(parts)

def check_extension_conformance(stage_dir: str, stage: str, stem: str, f: Findings) -> None:
    """AC-NAMING-17: file extensions used in root principal/stage-identifying
    filenames and Multi-Part named-part filenames SHOULD conform to industry
    best practice -- a well-known/registered rendering format in common OASIS
    use -- rather than a proprietary, cryptic, or invented extension token
    (Naming Directives Section 4, 'File extensions should conform to industry
    best practice -- matching well-known IANA MIME Media Types'). Candidates
    are derived from the package's already-known delivery `stem` (see
    _extension_conformance_candidates), so images, schemas, DTDs, WSDLs,
    XML/JSON instance artifacts, supporting documents, examples, test
    suites, and build/tooling files -- 'unconstrained other than for name
    character conformance' and 'generally subject to no special rules' per
    the same section -- are never walked or evaluated by this check, and
    coincidentally-named files that merely share the stage token are never
    misread as principal or named-part delivery files."""
    principal, parts = _extension_conformance_candidates(stage_dir, stage, stem)
    f.observe("extension-conformance",
              principal_files=principal or "(none)",
              named_part_files=parts or "(none)")
    principal_set = set(principal)
    for rel in list(principal) + list(parts):
        name = os.path.basename(rel)
        if name in EXTENSIONLESS_ALLOWLIST:
            continue
        _stem, dot, ext = name.rpartition(".")
        if not dot:
            continue  # extensionless is AC-NAMING-16's defect, not this SHOULD check's
        if ext.lower() not in EXTENSION_ALLOWLIST:
            kind = "principal/stage-identifying" if rel in principal_set else "Multi-Part named-part"
            f.add(WARN, "extension-conformance",
                  f"{kind} filename '{rel}' uses extension '.{ext}', "
                  f"which is not on this check's table of common OASIS publication "
                  f"rendering-format extensions; verify it follows the Naming Directives "
                  f"Section 4 file-extension best-practice guidance or confirm the format "
                  f"choice with Project Administration.")


# ===== AC-NAMING-18 (artifact-naming) =====
# AC-NAMING-18: Naming Directives s4/5.2/5.3 -- non-document-identifier
# artifacts (schemas, images, WSDLs, codelists, XML/JSON instances, and
# similar supporting files) should keep a stable, identical filename across
# releases; the directive's own counter-example is mySchema.xsd vs NOT
# mySchema-csd02.xsd. Vocabulary is DERIVED from the shared VALID_STAGE_
# PREFIXES / RETIRED_STAGE_TOKENS constants (module-level, reused by
# check_stage_name/check_version_naming) MINUS the tokens a corpus grep
# proves have zero attestation anywhere in naming-directives.txt: ps, psd,
# pn, pnd, csdpr, cndpr. Sec 5.2 enumerates the current set as exactly
# csd/cs/os/errata/cnd/cn (plus the informally-documented 'wd' substitution
# for unpublished working drafts); the v1.7 changelog's retired set is
# exactly csprd/cnprd/cos. Deriving from the shared constants (rather than
# a fully independent literal list) means this check's vocabulary tracks
# the shared source of truth automatically if it is ever cleaned up,
# while the exclusion set stays explicit and corpus-cited so today's
# behavior matches what the AC-NAMING-18 spec record verified. "os" is
# separately excluded from the digit-requiring arm because Sec 5.2 states
# the os stage abbreviation is never used with a revision number (a bare
# "-os" match would collide with ordinary words like logos.png/chaos.svg;
# deliberately not implemented -- see gating_note and rebuttals).
import re as _re

_UNATTESTED_STAGE_TOKENS = {"ps", "psd", "pn", "pnd"}
_UNATTESTED_RETIRED_TOKENS = {"csdpr", "cndpr"}
_STAGE_TOKENS_WITH_REVISION = sorted(
    (VALID_STAGE_PREFIXES - {"os"} - _UNATTESTED_STAGE_TOKENS)
    | (RETIRED_STAGE_TOKENS - _UNATTESTED_RETIRED_TOKENS),
    key=len, reverse=True)  # longest-first: csprd/cnprd/errata are tried
                             # before any shorter cs/cn/cs prefix they
                             # contain, so correctness never depends on
                             # backtracking retry semantics.
STAGE_REVISION_TOKEN = _re.compile(
    r"(?:^|[-_.])(" + "|".join(_STAGE_TOKENS_WITH_REVISION) + r")([0-9]{2})(?=$|[-_.])",
    _re.IGNORECASE)

# Package-management exemptions: EXACT README/LICENSE variants and actual
# checksum-manifest files only -- not any filename that merely starts with
# or contains those words. schemas/README-csd02.xsd and
# schemas/checksum-profile-csd02.xsd are real supporting artifacts, not
# documentation/manifest files, and must not be silently exempted.
_README_LICENSE = _re.compile(r"^(?:README|LICENSE)(?:\.[A-Za-z0-9]+)?$", _re.IGNORECASE)
_CHECKSUM_FILE = _re.compile(
    r"^(?:checksums?|sha(?:1|224|256|384|512)sums?|md5sums?)(?:\.[A-Za-z0-9]+)?$",
    _re.IGNORECASE)
_CHECKSUM_EXT = _re.compile(
    r"\.(?:sha1|sha224|sha256|sha384|sha512|md5)(?:sum)?$", _re.IGNORECASE)
_MANIFEST_FILE = _re.compile(r"^manifest\.(?:json|txt)$", _re.IGNORECASE)

# Extensions a legitimate Naming Directives document-identifier side-file
# (multi-part part, comment-resolution-log) can actually carry. A file
# whose stem happens to equal '<stem>-partN-<name>' or
# '<stem>-comment-resolution-log' but ships as .xsd/.wsdl/.json is NOT the
# prose side-file the exemption exists for -- it is a real artifact that
# coincidentally collides with the naming shape, and must still be scanned.
_DOC_IDENTIFIER_EXTS = {"md", "html", "htm", "pdf", "docx", "odt", "txt", "xls", "xlsx"}

def check_stable_artifact_names(stage_dir: str, items: dict, stem: str,
                                f: Findings) -> None:
    """AC-NAMING-18: a non-document-identifier artifact's own filename
    should not embed a stage+revision token (Naming Directives s4: "it is
    considered inadvisable to incorporate instance-specific [stage]
    [revision] data ... other than in the document identifier files ...
    thus mySchema.xsd but NOT mySchema-csd02.xsd"). TCs are advised to
    express release identity via named subdirectories instead, keeping a
    stable filename across successive releases.

    Exempt: the package's own delivery items (required to embed
    stage/revision), any file matching the delivery stem plus a
    recognized Naming Directives suffix -- multi-part (-partN-partName),
    public-review-metadata (-public-review-metadata.html, fixed
    extension per the directive's own grammar), or comment-resolution-log
    (-comment-resolution-log.<ext>) -- restricted to extensions a real
    prose/side-file document identifier actually carries (an .xsd/.wsdl/
    .json with that stem shape is a real artifact, not a side-file, and
    stays in scope), and package-management files (manifest.json,
    checksum manifests, exact README/LICENSE variants, anything under
    _audit/, OS/editor junk). NOTE: this tool has no shared, reusable
    document-identifier classifier that check_filenames/
    check_version_naming and this check could jointly call (verified:
    find_delivery_items only recognizes the package's OWN delivery items
    by extension, and check_filenames only computes a single stem
    string -- neither is a general-purpose Naming Directives filename
    classifier). The three side-file variants are therefore matched here
    directly against the exact Naming Directives grammar (corpus-verified:
    naming-directives.txt Sec 4's multi-part partNumber definition and
    public-review-metadata/comment-resolution-log worked examples), not a
    partial or approximate mirror of it. Extracting a genuine shared
    classifier that check_filenames/check_version_naming would also
    adopt is future work outside this check's surgical scope (it would
    change two other, independently-owned checks); see gating_note.

    Directory-path stage segments are never flagged: only the file's own
    basename is inspected -- a file living under a stage-numbered
    directory (.../csd02/schemas/mySchema.xsd) is the directive's
    recommended pattern, not a defect. Guards malformed inputs (items is
    None or contains non-path values, stage_dir missing) by scanning zero
    files rather than raising. A no-op when the package carries no
    non-exempt file at all."""
    items = {k: v for k, v in (items or {}).items() if isinstance(v, str)}
    stem = stem or ""
    delivery_names = {os.path.basename(p) for p in items.values()}
    if stem:
        delivery_names.add(stem + ".zip")  # the package zip carries the full stem by design

    multipart_pat = crl_pat = None
    pr_metadata_name = ""
    if stem:
        esc = re.escape(stem)
        multipart_pat = re.compile(
            rf"^{esc}-part\d+-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", re.IGNORECASE)
        crl_pat = re.compile(rf"^{esc}-comment-resolution-log$", re.IGNORECASE)
        pr_metadata_name = f"{stem}-public-review-metadata.html".lower()

    scanned = matched = 0
    hits = []
    if stage_dir and os.path.isdir(stage_dir):
        for root, dirs, files in os.walk(stage_dir):
            dirs[:] = [d for d in dirs if d not in JUNK_DIRS and d != "_audit"]
            for name in files:
                if name in delivery_names or name in JUNK_NAMES:
                    continue
                if name.endswith(("~", ".bak", ".orig", ".swp")):
                    continue
                if _MANIFEST_FILE.match(name) or name.lower().endswith("-manifest.txt"):
                    continue
                if _README_LICENSE.match(name):
                    continue
                if _CHECKSUM_FILE.match(name) or _CHECKSUM_EXT.search(name):
                    continue
                if name.lower() == pr_metadata_name:
                    continue
                base, ext = os.path.splitext(name)
                ext_l = ext.lstrip(".").lower()
                if ext_l in _DOC_IDENTIFIER_EXTS and (
                        (multipart_pat and multipart_pat.match(base)) or
                        (crl_pat and crl_pat.match(base))):
                    continue
                scanned += 1
                # Search the FULL basename (not the extension-stripped stem):
                # os.path.splitext only strips the final dot segment, so a
                # token placed after a content extension (mySchema.xsd-csd02)
                # would otherwise never be seen.
                found = list(STAGE_REVISION_TOKEN.finditer(name))
                if found:
                    matched += 1
                    rel = os.path.relpath(os.path.join(root, name), stage_dir)
                    token, digits = found[0].group(1), found[0].group(2)
                    suggested = STAGE_REVISION_TOKEN.sub("", name)
                    suggested = re.sub(r"[-_.]{2,}", "-", suggested).strip("-_.") or name
                    hits.append((rel, token, digits, suggested))
    f.observe("artifact-naming", supporting_files_scanned=scanned,
              stage_revision_matches=matched)
    for rel, token, digits, suggested in sorted(hits):
        f.add(WARN, "artifact-naming",
              f"{rel}: filename embeds a stage/revision token "
              f"('{token}{digits}') outside the delivery items; Naming "
              f"Directives s4 advises against instance-specific [stage]"
              f"[revision] data in artifact filenames (thus mySchema.xsd "
              f"but NOT mySchema-csd02.xsd) -- keep a stable name across "
              f"releases and express the release via the directory path "
              f"instead. Suggested stable name: {suggested}. If "
              f"'{token}{digits}' is not actually an OASIS stage/revision "
              f"token (e.g. a coordinate-system, LDAP CN, or unrelated "
              f"product-version identifier), this warning is a false "
              f"positive -- verify before renaming.")


# ===== AC-NAMING-19 (multi-part-naming) =====
PART_EXT = ("md", "docx", "odt", "html", "pdf")

# Naming Directives Multi-Part filename grammar (worked example:
# saml-v2.1-csd01-part1-overview). The revision-number digits are required
# for every stage EXCEPT os ('the os stage abbreviation is never used with a
# revision number') -- the stage/revision alternative below is built directly
# from the tool's own stage-abbrev authority (VALID_STAGE_PREFIXES) so
# os-with-a-revision ("os01") and non-os-without-a-revision ("csd") are both
# correctly excluded as off-grammar rather than silently admitted. wp/partname
# groups admit internal hyphens AND underscores per corpus-attested hyphenated
# WP-abbrev (security-playbooks), multi-word part titles (username-token-
# profile), and the Naming Directives' own allowance of underscores in
# filenames (Sec 3: "The UNDERSCORE character may be used in filenames and
# directory names ... An UNDERSCORE must never be used in a filename or
# directory name that is used in a document URI" -- this is a filename token,
# not a URI segment, so underscore is legal here). version-id accepts upper-
# or lower-case 'v' (v1.0 / V1.0) so a case-only divergence between two parts
# is captured and still fires this check's deliberately case-sensitive token
# comparison, rather than one variant being silently dropped by the regex.
_NON_OS_STAGE_ALT = "|".join(sorted(VALID_STAGE_PREFIXES - {"os"}, key=len, reverse=True))
PART_STEM_RE = re.compile(
    r"^(?P<wp>[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*)-(?P<ver>[vV]\d+(?:\.\d+){1,2})-"
    rf"(?P<stage>os|(?:{_NON_OS_STAGE_ALT})\d{{2}})-part(?P<partnum>\d+)-"
    r"(?P<partname>[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*)$")

# Multi-Part Option 1 URI part-subdirectory segment: [partNumber]-[partName].
# This models a URI path segment (Naming Directives Sec 3), where underscores
# must NEVER appear -- unlike PART_STEM_RE above, which models a filename
# token where underscores ARE permitted. Keep this pattern strict.
PART_SUBDIR_RE = re.compile(r"^part\d+-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")

def check_multipart_naming(stage_dir: str, f: Findings) -> None:
    """AC-NAMING-19: every constituent part of a Multi-Part Work Product
    (Naming Directives filename grammar, staged flat at the stage-directory
    root or nested one level under a <partNumber>-<partName>/ subdirectory
    per the Option 1 URI structure) must embed the identical WP-abbrev and
    identical version-id token. TC Process 2.2.3: a multi-part Work Product
    'must have a single Work Product name and version number'; the Handbook
    restates it 'across all parts.' This is a filename-token proxy for that
    identity mandate, not a read of the Work Product's registration record.
    A silent no-op when the package is not lexically identified as multi-part
    (fewer than two distinct (partnum, partname) combinations found)."""
    matches: list[tuple[str, re.Match]] = []
    subdirs_scanned: list[str] = []
    subdirs_unreadable: list[str] = []
    if not isinstance(stage_dir, (str, bytes, os.PathLike)):
        f.observe("multi-part-naming", scanned_root="(unreadable)",
                  part_grammar_files=0, distinct_parts=0)
        return
    try:
        root_names = sorted(os.listdir(stage_dir))
    except (OSError, TypeError, ValueError):
        f.observe("multi-part-naming", scanned_root="(unreadable)",
                  part_grammar_files=0, distinct_parts=0)
        return
    for name in root_names:
        p = os.path.join(stage_dir, name)
        if os.path.isfile(p):
            ext = os.path.splitext(name)[1].lstrip(".").lower()
            if ext not in PART_EXT:
                continue
            m = PART_STEM_RE.match(os.path.splitext(name)[0])
            if m:
                matches.append((name, m))
        elif os.path.isdir(p) and PART_SUBDIR_RE.match(name):
            subdirs_scanned.append(name)
            try:
                sub_names = sorted(os.listdir(p))
            except (OSError, TypeError, ValueError):
                subdirs_unreadable.append(name)
                continue
            for sname in sub_names:
                sp = os.path.join(p, sname)
                if not os.path.isfile(sp):
                    continue
                ext = os.path.splitext(sname)[1].lstrip(".").lower()
                if ext not in PART_EXT:
                    continue
                m = PART_STEM_RE.match(os.path.splitext(sname)[0])
                if m:
                    matches.append((f"{name}/{sname}", m))

    parts = {(m.group("partnum"), m.group("partname")) for _rel, m in matches}
    f.observe("multi-part-naming",
              part_subdirs_scanned=subdirs_scanned,
              part_subdirs_unreadable=subdirs_unreadable,
              matched_part_grammar_files=[rel for rel, _m in matches],
              part_grammar_files=len(matches), distinct_parts=len(parts))
    if len(parts) < 2:
        return  # not lexically identified as multi-part: no-op

    wps = {m.group("wp") for _rel, m in matches}
    vers = {m.group("ver") for _rel, m in matches}
    f.observe("multi-part-naming", wp_abbrev_tokens=wps, version_id_tokens=vers)

    # Group matches by (partnum, partname) for REPORTING only (spec step 5):
    # collapses each part's own md/html/pdf/docx siblings into one entry per
    # part so a mismatch across many-format many-part packages does not list
    # dozens of near-duplicate offenders. If a part's OWN siblings internally
    # disagree on the axis being reported (a sibling-level mismatch inside one
    # part), every disagreeing sibling of that part is kept rather than
    # collapsed, so that divergence is never hidden by the grouping. The
    # wp/ver DIVERGENCE DETECTION above (wps/vers) always runs over every
    # individual matched filename regardless of this grouping.
    by_part: dict[tuple[str, str], list[tuple[str, re.Match]]] = {}
    for rel, m in matches:
        by_part.setdefault((m.group("partnum"), m.group("partname")), []).append((rel, m))

    def _reporting_set(token_key: str) -> list[tuple[str, re.Match]]:
        out: list[tuple[str, re.Match]] = []
        for members in by_part.values():
            members = sorted(members, key=lambda pair: pair[0])
            if len({m.group(token_key) for _r, m in members}) > 1:
                out.extend(members)
            else:
                out.append(members[0])
        return out

    if len(wps) > 1:
        offenders = sorted(f"{rel} (wp={m.group('wp')})" for rel, m in _reporting_set("wp"))
        f.add(BLOCKER, "multi-part-naming",
              f"Multi-Part Work Product filenames use inconsistent WP-abbrev tokens "
              f"across parts, contrary to the Naming Directives Multi-Part grammar "
              f"and the single Work Product name required by TC Process 2.2.3: "
              f"{', '.join(offenders)}")
    if len(vers) > 1:
        offenders = sorted(f"{rel} (ver={m.group('ver')})" for rel, m in _reporting_set("ver"))
        f.add(BLOCKER, "multi-part-naming",
              f"Multi-Part Work Product filenames use inconsistent version-id tokens "
              f"across parts, contrary to the Naming Directives Multi-Part grammar "
              f"and the single Work Product version number required by TC Process "
              f"2.2.3: {', '.join(offenders)}")


# ===== AC-NAMING-20 (multi-part-naming) =====
# AC-NAMING-20: Multi-Part Work Product part-identifier grammar. Distinct
# from the AC-NAMING-19 WP-abbrev/version-id consistency check (which only
# ever examines filenames that ALREADY carry a well-formed -partN-name
# segment); this check also catches filenames that share a package's
# <wp>-<version>-<stage> core but are MISSING, malformed, or mis-numbered on
# that segment. Named distinctly (MULTIPART_* / check_multipart_part_
# identifiers) so it does not collide with AC-NAMING-19's PART_EXT /
# PART_SUBDIR_RE / check_multipart_naming once both are merged.
# MULTIPART_STAGE_TRACK_PREFIXES: Standards Track CSD/CS/OS and
# Non-Standards Track CND/CN only (spec stage_track_gating); WD, the
# retired CSPRD/CNPRD tokens, PS/PSD/PN/PND, and Approved Errata (handled
# separately, see the errata regex below) are out of scope.
MULTIPART_FILE_EXTS = {"html", "pdf", "md", "docx", "odt"}
MULTIPART_PART_SUBDIR_RE = re.compile(
    r"^part(\d+)-([A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)$")
MULTIPART_PART_TAIL_RE = re.compile(
    r"^-part(\d+)-([A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)$")
MULTIPART_COMPANION_SUFFIXES = ("-public-review-metadata", "-comment-resolution-log", "-DIFF", "-diff")
MULTIPART_STAGE_TRACK_PREFIXES = frozenset({"csd", "cs", "os", "cnd", "cn"})

def check_multipart_part_identifiers(stage_dir: str, version: str, stage: str,
                                     f: Findings) -> None:
    """AC-NAMING-20: a Multi-Part Work Product's delivery filenames insert
    -part<N>-<name> between the stage core and the extension (Naming
    Directives v1.7 s4 'Name Construction Rules for Files and Directories';
    handbook-Naming.txt 'Multi-part work products'), the numerals starting
    at 1 and increasing monotonically with no gaps and no number reused for
    two differently named parts. Skipped for Approved-Errata stage
    directories (own list-of-corrections / complete-incorporating-errata
    convention, naming-directives.txt s4 Applicability) and for stage
    directories outside Standards Track CSD/CS/OS or Non-Standards Track
    CND/CN (spec stage_track_gating). A silent no-op when the package's
    delivery filenames do not resolve to one unambiguous
    <wp>-<version>-<stage> core (left to the filenames/version-naming check
    family), or resolve to fewer than two distinct tails on that core (not
    lexically identified as multi-part)."""
    if re.fullmatch(r"errata\d*", stage):
        f.observe("multi-part-naming", naming20_skipped="errata stage")
        return
    sm = re.fullmatch(r"([a-z]+)(\d\d)?", stage)
    stage_prefix = sm.group(1) if sm else stage
    if stage_prefix not in MULTIPART_STAGE_TRACK_PREFIXES:
        f.observe("multi-part-naming",
                  naming20_skipped=f"stage track '{stage_prefix}' out of scope "
                  f"(Standards Track CSD/CS/OS, Non-Standards Track CND/CN only)")
        return
    entries: list[tuple[str, str, str | None]] = []
    try:
        root_names = sorted(os.listdir(stage_dir))
    except OSError:
        f.observe("multi-part-naming", naming20_skipped="stage directory unreadable")
        return
    for name in root_names:
        p = os.path.join(stage_dir, name)
        if os.path.isfile(p):
            stem, ext = os.path.splitext(name)
            ext = ext.lstrip(".").lower()
            if ext in MULTIPART_FILE_EXTS:
                entries.append((stem, ext, None))
        elif os.path.isdir(p) and MULTIPART_PART_SUBDIR_RE.fullmatch(name):
            try:
                sub_names = sorted(os.listdir(p))
            except OSError:
                continue
            for sname in sub_names:
                sp = os.path.join(p, sname)
                if not os.path.isfile(sp):
                    continue
                stem, ext = os.path.splitext(sname)
                ext = ext.lstrip(".").lower()
                if ext in MULTIPART_FILE_EXTS:
                    entries.append((stem, ext, name))

    if not entries:
        f.observe("multi-part-naming", naming20_entries_scanned=0)
        return

    # Resolve CORE = "<wp-abbrev>-<version>-<stage>" from the raw on-disk
    # stems, boundary-anchored: the marker must be preceded by at least one
    # wp-abbrev character (idx > 0) and followed by end-of-string or a
    # hyphen, so a revision digit-bleed like "csd010" cannot masquerade as a
    # "csd01" match, and an unrelated stem cannot silently absorb into the
    # wrong package's core. Companion artifacts are NOT excluded before this
    # step -- they also carry the marker and agree on the same core as the
    # real parts, so including them cannot introduce ambiguity; excluding
    # them only after CORE is known (below) avoids the chicken-and-egg
    # problem of an exact-match exclusion that needs CORE before it can run.
    marker = f"-{version}-{stage}"
    cores: set[str] = set()
    for stem, _ext, _sub in entries:
        idx = stem.find(marker)
        while idx != -1:
            end = idx + len(marker)
            if idx > 0 and (end == len(stem) or stem[end] == "-"):
                cores.add(stem[:end])
            idx = stem.find(marker, idx + 1)
    f.observe("multi-part-naming", naming20_entries_scanned=len(entries),
              naming20_cores_resolved=sorted(cores) or "(none)")
    if len(cores) != 1:
        return  # no single resolvable WP core: the filenames/version-naming
                 # check family already covers this case (or two genuinely
                 # distinct packages share one directory -- unresolvable
                 # from filenames alone, a disclosed residual limitation)
    core = cores.pop()

    # Exclude the two registered CORE-prefixed companion artifacts by EXACT
    # stem match (not endswith): a genuine part whose own partName happens
    # to end with one of these literal suffixes (e.g.
    # "<core>-part1-public-review-metadata") is a real part, not the
    # registered companion file, and must not be silently discarded.
    companion_stems = {core + suf for suf in MULTIPART_COMPANION_SUFFIXES}
    entries = [e for e in entries if e[0] not in companion_stems]

    in_scope = [(stem, ext, sub) for stem, ext, sub in entries
                if stem == core or stem.startswith(core + "-")]
    tails = {stem[len(core):] for stem, _ext, _sub in in_scope}
    f.observe("multi-part-naming", naming20_core=core,
              naming20_distinct_tails=sorted(tails))
    if len(tails) < 2:
        return  # single-part package: this check does not apply

    # Group by distinct stem so a violated stem shipped as md/html/pdf/docx
    # produces exactly one finding, not one per format variant.
    by_stem: dict[str, list[tuple[str, str | None]]] = {}
    for stem, ext, sub in in_scope:
        by_stem.setdefault(stem, []).append((ext, sub))

    number_names: dict[int, set[str]] = {}
    reported_subdir_mismatch: set[tuple[str, str]] = set()
    for stem in sorted(by_stem):
        tail = stem[len(core):]
        pairs = by_stem[stem]
        rep_ext = sorted(ext for ext, _sub in pairs)[0]
        if tail == "":
            f.add(BLOCKER, "multi-part-naming",
                  f"{stem}.{rep_ext}: bare canonical filename in a multi-part package "
                  f"(other delivery files sharing '{core}' carry part identifiers).")
            continue
        pm = MULTIPART_PART_TAIL_RE.match(tail)
        if not pm:
            f.add(BLOCKER, "multi-part-naming",
                  f"{stem}.{rep_ext}: missing part identifier -- a multi-part "
                  f"delivery filename must insert -part<N>-<name> between the "
                  f"stage core and the extension (Naming Directives v1.7 s4).")
            continue
        number_str, pname = pm.group(1), pm.group(2)
        number = int(number_str)
        for sub in sorted({s for _e, s in pairs if s}):
            sm2 = MULTIPART_PART_SUBDIR_RE.fullmatch(sub)
            if not sm2:
                continue
            expected = f"part{number_str}-{pname}"
            if sub != expected and (stem, sub) not in reported_subdir_mismatch:
                reported_subdir_mismatch.add((stem, sub))
                f.add(BLOCKER, "multi-part-naming",
                      f"{stem}.{rep_ext}: part filename and containing part-directory "
                      f"disagree (directory '{sub}/' implies part {sm2.group(1)}-"
                      f"{sm2.group(2)}, filename implies part {number_str}-{pname}).")
        number_names.setdefault(number, set()).add(pname)

    for number, names in sorted(number_names.items()):
        if len(names) > 1:
            f.add(BLOCKER, "multi-part-naming",
                  f"'{core}': part number reused for different parts -- part "
                  f"{number} maps to both {' and '.join(sorted(names))}.")

    numbers = sorted(number_names)
    if numbers and numbers[0] != 1:
        f.add(BLOCKER, "multi-part-naming",
              f"'{core}': part numbering does not begin at 1 (lowest part "
              f"number found is {numbers[0]}); Naming Directives v1.7 s4 "
              f"requires numbering to start at 1.")
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        f.add(BLOCKER, "multi-part-naming",
              f"'{core}': part numbering is not monotonically increasing / "
              f"contains a gap (found {numbers}); Naming Directives v1.7 s4 "
              f"requires consecutive numbering with no gaps.")


# ===== AC-NAMING-21 (public-review-metadata) =====
def check_public_review_metadata(base: str, stage: str, stem: str,
                                 f: Findings) -> None:
    """Naming Directives v1.7 s5.2 / TC Handbook Naming: a published csd/cnd
    stage directory that underwent a TC public review must carry a companion
    "public review metadata" file -- [WP-abbrev]-[version-id]-[stage-abbrev]
    [revisionNumber]-public-review-metadata.html -- published there by
    Project Administration. POST-PUBLICATION AUDIT ONLY: reads the LIVE
    docs.oasis-open.org stage directory (never the local TC-submitted
    package), mirroring check_revision_collision's network pattern including
    its PUB_CHECK_OFFLINE silent-skip. Fires only for csd/cnd stage tokens
    (naming-directives.txt 5.2 ties this file to 'the directory with the CSD
    or CND'), using the identical stage-prefix regex check_stage_name uses.
    Never asserts BLOCKER without definitive evidence that this exact
    revision underwent review: Tier 1 (a same-revision comment-resolution-log
    already live in the stage directory), Tier 2 (csd only -- a downstream
    cs/errata stage directory whose own published Previous-stage cover URL,
    extracted the same way check_html_cover/stage_urls_from_md parse it,
    resolves to this csd's own base URL), or Tier 3 (an operator-declared
    PUB_CHECK_PUBLIC_REVIEW_OPEN=1 run-context assertion). Absent all three,
    or if the stage directory itself could not be scanned, the check degrades
    to an advisory INFO rather than a false BLOCKER (public review is
    optional for CND, and a csd/cnd may simply not have been submitted for
    review yet -- and an unreachable directory proves nothing about absence)."""
    m = re.fullmatch(r"([a-z]+)(\d\d)?", stage) if isinstance(stage, str) else None
    doc_stage_token = m.group(1) if m else (stage if isinstance(stage, str) else "")
    if doc_stage_token not in ("csd", "cnd"):
        return
    if os.getenv("PUB_CHECK_OFFLINE", "").lower() in {"1", "true", "yes"}:
        return
    if not base or not base.startswith(SITE + "/") or not stem:
        return

    import urllib.error
    import urllib.request

    def fetch(url: str) -> tuple[int, str]:
        req = urllib.request.Request(url, headers={"User-Agent": "pub-check"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, r.read(65536).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    def href_filenames(listing: str) -> set[str]:
        # same-directory filenames only (no '/' left after stripping query/
        # fragment); quote-agnostic and case-insensitive on the attribute
        # name, percent-decoded so a scraped '%2E' doesn't dodge comparison.
        names = set()
        for h in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', listing, re.I):
            path = h.split("?", 1)[0].split("#", 1)[0]
            if not path or "/" in path:
                continue
            names.add(urllib.parse.unquote(path))
        return names

    status, listing = fetch(base)
    live_names = href_filenames(listing) if status == 200 else set()
    f.observe("public-review-metadata", stage_directory_url=base,
              http_status=status or "(unreachable)",
              live_filenames=sorted(live_names) or "(none)")

    expected = f"{stem}-public-review-metadata.html"
    resolution_re = re.compile(
        rf"^{re.escape(stem)}-comment-resolution-log\.[A-Za-z0-9]+$")

    tier = ""
    tier_detail: dict = {}
    if status == 200 and any(resolution_re.match(n) for n in live_names):
        tier = "Tier 1 (a comment-resolution-log for this revision is already live)"
    elif doc_stage_token == "csd":
        version_url = base.split(f"/{stage}/", 1)[0] + "/"
        vstatus, vlisting = fetch(version_url)
        if vstatus == 200 and vlisting:
            siblings = sorted(set(re.findall(r'href="((?:cs|errata)\d*)/"', vlisting)))
            base_path = uri_path(base).rstrip("/")
            for sib in siblings:
                sib_stem = re.sub(rf"-{re.escape(stage)}$", f"-{sib}", stem)
                sib_base = f"{version_url}{sib}/"
                hstatus, shtml = fetch(f"{sib_base}{sib_stem}.html")
                if hstatus != 200 or not shtml:
                    continue
                head = re.sub(r"<[^>]+>", " ", shtml)
                head = re.sub(r"&nbsp;|&#160;|\s+", " ", head)
                pm = re.search(
                    r"Previous (Stage|Version)\b(.*?)(?=Latest (Stage|Version)|"
                    r"Technical Committee|$)", head, re.I | re.S)
                prev_urls = (re.findall(r"https?://docs\.oasis-open\.org/\S+", pm.group(2))
                             if pm else [])
                if any(uri_path(u).rstrip("/") == base_path for u in prev_urls):
                    tier = (f"Tier 2 (downstream /{sib}/ stage's own Previous-stage "
                             f"cover URL resolves to this csd's base URL)")
                    tier_detail = {"tier2_sibling": sib_base,
                                    "tier2_previous_stage_urls": prev_urls or "(none)"}
                    break
    if not tier and os.getenv("PUB_CHECK_PUBLIC_REVIEW_OPEN", "").lower() in {"1", "true", "yes"}:
        tier = "Tier 3 (operator-declared public review for this revision)"

    if not tier:
        f.add(INFO, "public-review-metadata",
              f"Could not confirm from the published record whether {stage} underwent "
              f"a TC public review (no live comment-resolution-log for this revision, "
              f"no downstream cs/errata stage evidence found). Manually confirm with "
              f"TC Admin; if a public review was opened, {expected} must be present "
              f"per Naming Directives v1.7 s5.2 / TC Handbook Naming.")
        return

    if tier_detail:
        f.observe("public-review-metadata", **tier_detail)

    if status != 200:
        # Tier evidence proves review occurred, but the stage directory
        # itself could not be scanned this run: absence is not provable,
        # so this stays advisory rather than a false BLOCKER.
        f.add(INFO, "public-review-metadata",
              f"{stage} underwent a TC public review ({tier}) but the live stage "
              f"directory {base} could not be scanned this run (http status "
              f"{status or '(unreachable)'}); cannot confirm whether {expected} is "
              f"present. Retry once the directory is reachable.")
        return

    if expected in live_names:
        fstatus, fcontent = fetch(base + expected)
        f.observe("public-review-metadata", review_evidence_tier=tier,
                  expected_filename=expected,
                  companion_http_status=fstatus or "(unreachable)")
        if fstatus == 200 and len(fcontent) == 0:
            f.add(WARN, "public-review-metadata",
                  f"{expected} exists at {base} but is empty (0 bytes); confirm its "
                  f"content actually documents the public review (a separate, "
                  f"not-yet-implemented content-validation check).")
        elif fstatus != 200:
            f.add(WARN, "public-review-metadata",
                  f"{expected} is listed at {base} but could not be fetched to "
                  f"confirm its content (http status {fstatus or '(unreachable)'}); "
                  f"investigate manually.")
        return

    f.add(BLOCKER, "public-review-metadata",
          f"{stage} underwent a TC public review ({tier}) but the live stage directory "
          f"{base} does not carry the required companion file {expected}. Naming "
          f"Directives v1.7 s5.2: 'Project Administration will publish an additional "
          f"\"public review metadata\" file in the directory with the CSD or CND'; "
          f"TC Handbook Naming: 'Work products undergoing public review must include "
          f"a companion metadata file.'")


# ===== AC-NAMING-22 (comment-resolution-log) =====
# AC-NAMING-22 helpers (naming-directives.txt s5.2): filename-pattern check
# for the comment-resolution-log that may accompany a CSD/CND stage
# directory's public-review-metadata file. Whitelist mirrors the corpus's
# own worked example plus the formats attested elsewhere in the corpus.
COMMENT_LOG_EXTS = frozenset({
    "txt", "xls", "xlsx", "pdf", "md", "doc", "docx", "csv", "ods", "htm", "html",
})

# Multi-Part Work Product lexical detection (Option-1 [partN]-[partName]/
# subdirectory scheme, Option-2 flat -partN-partName filename scheme) --
# same grammar shape the AC-NAMING-19 multi-part-naming check already uses,
# so this check excludes multi-part packages the same way that one does,
# pending the TC Admin per-part-vs-whole-package policy call. AC-NAMING-19
# is not yet merged into this file (no live collision today; grepped and
# confirmed at fixer time). If/when it merges first, fold these into its
# PART_SUBDIR_RE/part-file grammar instead of keeping a second near-
# duplicate pair (per the independent verifier's helpers-duplication note
# -- non-blocking, explicitly called out as a merge-time architecture
# choice, not a correctness gate).
COMMENT_LOG_PART_FILE_RE = re.compile(
    r"-part\d+-[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$", re.IGNORECASE)
COMMENT_LOG_PART_SUBDIR_RE = re.compile(
    r"^part\d+-[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$", re.IGNORECASE)

# The downstream-stage tokens that prove a CSD/CND public review has
# concluded (tc-process.txt s2.7: the downstream approval ballot "may only
# commence once each comment... has been resolved"): a later cs/os/errata
# sibling for a csd gate, a later cn sibling for a cnd gate.
COMMENT_LOG_DOWNSTREAM_RE = {
    "csd": re.compile(r"^(cs\d{2}|os|errata\d{2})$"),
    "cnd": re.compile(r"^cn\d{2}$"),
}


def _comment_log_normalize(name: str) -> str:
    """Lower-cased form of a basename with ONLY the two Naming Directives
    word-joining separators removed (hyphen, underscore) -- deliberately
    NARROWER than a full punctuation strip. This still tolerates the
    hyphen/underscore/camelCase misnamings the corpus's own worked example
    exhibits (e.g. the "CommentResolutionLog-DRAFT" near-miss fixture),
    but leaves every OTHER separator a filename might use -- a dot, a
    plus sign, a space -- intact, so an unrelated file whose name merely
    runs the words "comment"/"resolution"/"log" together ACROSS one of
    those other separators (e.g. "why.comment.resolution.log.is-not-
    required.md", "comment+resolution+log-notes.txt") does not collapse
    into a false contiguous-substring match the way a strip-all-
    punctuation normalizer would."""
    return re.sub(r"[-_]", "", name.lower())


def _comment_log_is_near_miss(probe: str, expected_basename: str) -> bool:
    """Whether an extension-stripped basename is a near-miss attempt at
    the comment-resolution-log filename per naming-directives.txt s5.2:
    its hyphen/underscore-normalized lower-cased form contains
    "commentresolutionlog" as a contiguous substring, or equals the
    expected basename's own normalized form. Only word-joining
    punctuation is folded away (see _comment_log_normalize); a genuinely
    unrelated file separated by other punctuation is not caught here."""
    stripped = _comment_log_normalize(probe)
    expected_stripped = _comment_log_normalize(expected_basename)
    return "commentresolutionlog" in stripped or stripped == expected_stripped


def _comment_log_is_multipart(stage_dir: str) -> bool:
    """Whether this stage directory is lexically identified as a Multi-Part
    Work Product (any Option-1 part-subdirectory or Option-2 flat part
    filename at the root). Guarded: an unreadable or malformed
    (non-PathLike) directory reads as not-multi-part rather than
    raising."""
    try:
        names = os.listdir(stage_dir)
    except (OSError, TypeError):
        return False
    for name in names:
        p = os.path.join(stage_dir, name)
        if os.path.isdir(p) and COMMENT_LOG_PART_SUBDIR_RE.match(name):
            return True
        if os.path.isfile(p):
            base, dot, _ext = name.rpartition(".")
            if dot and COMMENT_LOG_PART_FILE_RE.search(base):
                return True
    return False


def _comment_log_downstream_sibling(stage_dir: str, prefix: str) -> str:
    """Name of a later-stage sibling directory (cs/os/errata for a csd
    gate, cn for a cnd gate) alongside this stage directory, or '' if none
    is found -- the review-concluded closure signal. `prefix` is the
    already-derived stage-family token ("csd"/"cnd"/...); the caller
    computes it once and passes it in rather than this helper re-parsing
    `stage` a second time. Guarded: an unreadable/nonexistent version
    directory, or a malformed (non-PathLike) stage_dir, reads as no
    evidence rather than raising."""
    pattern = COMMENT_LOG_DOWNSTREAM_RE.get(prefix)
    if pattern is None:
        return ""
    try:
        version_dir = os.path.dirname(os.path.normpath(stage_dir))
        this_name = os.path.basename(os.path.normpath(stage_dir))
        names = sorted(os.listdir(version_dir))
    except (OSError, TypeError):
        return ""
    for name in names:
        if (name != this_name and pattern.match(name)
                and os.path.isdir(os.path.join(version_dir, name))):
            return name
    return ""

def check_comment_resolution_log(stage_dir: str, stage: str, stem: str,
                                 f: Findings) -> None:
    """AC-NAMING-22 (naming-directives.txt s5.2): for a CSD/CND stage
    directory that itself carries a public-review-metadata file (Project
    Administration publishes this only once a TC has resolved via Work
    Product Ballot to open a public review for THAT stage/revision), a
    comment-resolution-log file present in the same directory must carry
    the exact basename [stem]-comment-resolution-log -- a misnamed-but-
    present log is a genuine, unconditional Naming Directives filename
    defect (BLOCKER), fired regardless of review-closure evidence.

    Absence of the log is never a BLOCKER on its own: naming-directives.txt
    conditions log production on the TC actually producing one ("When the
    TC produces the required comment resolution log..."), that production
    sits "following the public review" (a legitimate multi-week window),
    and handbook-PublicReviews.txt states the underlying TC Process s2.6
    obligation (track comments, post disposition to the TC's e-mail lists)
    is "a matter of best practice" as to HOW it is recorded -- satisfiable
    without ever publishing this file. Absence surfaces as an evidence-
    bounded WARN only when a later-stage sibling directory shows the
    review has demonstrably concluded (tc-process.txt s2.7: the downstream
    approval ballot "may only commence once each comment... has been
    resolved"); otherwise it is NOT APPLICABLE (open review, or resolution
    work still in progress -- absence is the expected, compliant state).

    Multi-Part Work Products are excluded entirely (NOT APPLICABLE)
    pending a TC Admin decision on per-part-vs-whole-package log scope.
    This check verifies only a filename pattern; it never claims to have
    validated a matched file's content or completeness.

    Guarded against malformed call-site input (non-string stage_dir/stage)
    as an observed not-applicable rather than a crash -- defense in depth;
    run()'s own contract always supplies strings, but a check must never
    take down the whole gate on a caller bug."""
    if not isinstance(stage_dir, str) or not isinstance(stage, str):
        f.observe("comment-resolution-log",
                  gate="not applicable: malformed stage_dir/stage input")
        return
    m = re.fullmatch(r"([a-z]+)(\d\d)?", stage or "")
    prefix = m.group(1) if m else (stage or "")
    if prefix not in {"csd", "cnd"}:
        f.observe("comment-resolution-log",
                  gate=f"not applicable: stage '{stage}' is not csd/cnd")
        return
    if not stem:
        f.observe("comment-resolution-log",
                  gate="not applicable: no established delivery stem")
        return
    if _comment_log_is_multipart(stage_dir):
        f.observe("comment-resolution-log",
                  gate="not applicable: Multi-Part Work Product (scope open_question)")
        return
    try:
        names = os.listdir(stage_dir)
    except (OSError, TypeError):
        f.observe("comment-resolution-log",
                  gate="not applicable: stage directory unreadable")
        return
    siblings = [n for n in names if os.path.isfile(os.path.join(stage_dir, n))]

    metadata_basename = f"{stem}-public-review-metadata.html"
    present = metadata_basename in siblings
    f.observe("comment-resolution-log",
              public_review_metadata_expected=metadata_basename,
              public_review_metadata_present=present,
              siblings_scanned=len(siblings))
    if not present:
        # NOT APPLICABLE: no in-package signal a public review was opened
        # for this stage instance (never a claim it did not happen).
        return

    expected_basename = f"{stem}-comment-resolution-log"
    f.observe("comment-resolution-log", expected_log_basename=expected_basename)

    exact_match = ""
    for name in siblings:
        base, dot, ext = name.rpartition(".")
        if dot and ext.lower() in COMMENT_LOG_EXTS and base == expected_basename:
            exact_match = name
            break
    f.observe("comment-resolution-log", exact_match=exact_match or "(none)")
    if exact_match:
        return  # PASS: correctly named comment-resolution-log is present

    near_miss = ""
    for name in siblings:
        base, dot, _ext = name.rpartition(".")
        probe = base if dot else name
        if _comment_log_is_near_miss(probe, expected_basename):
            near_miss = name
            break

    if near_miss:
        f.add(BLOCKER, "comment-resolution-log",
              f"Public-review-metadata file present ({metadata_basename}); a "
              f"file resembling the required comment-resolution-log is present "
              f"but misnamed: found \"{near_miss}\", expected "
              f"\"{expected_basename}.[ext]\" per naming-directives.txt §5.2.")
        return

    downstream = _comment_log_downstream_sibling(stage_dir, prefix)
    f.observe("comment-resolution-log", downstream_sibling=downstream or "(none)")
    if not downstream:
        # NOT APPLICABLE: no in-scope evidence the review has concluded;
        # absence here is the expected, compliant state (open review, or
        # comment-resolution work still in progress).
        return

    f.add(WARN, "comment-resolution-log",
          f"Public review for {stem} appears to have concluded (a later "
          f"{downstream} package exists in scope) but no file matching "
          f"{expected_basename}.[ext] was found in this directory. Publishing "
          f"a comment-resolution-log under this basename is customary/best-"
          f"practice per the Handbook, not an unconditional Naming Directives "
          f"existence mandate; the TC Process §2.6/§2.7 obligation "
          f"(track comments, post disposition to the primary/comment e-mail "
          f"lists) may already be satisfied by a record outside this package, "
          f"or the review may have received zero comments. Confirm the "
          f"disposition record exists, by this file or another channel, "
          f"before treating this as a defect.")


# ===== AC-PACKAGING-05 (normdef-refs) =====
import unicodedata

# AC-PACKAGING-05 / TC Process 2.2.5: Standards Track stage prefixes (any
# revision number). Non-Standards Track (cnd, cn) and unmapped stage tokens
# (wd, ps, psd, pn, pnd) are not-applicable pending TC Admin confirmation.
STANDARDS_TRACK_PREFIXES = {"csd", "cs", "os", "errata"}

# The extension allowlist 2.2.5 itself names (XML instances -> .xml, Java
# code -> .java) plus established schema/grammar extensions. General-purpose
# source-code extensions (.py, .c, .h, .cs, .js) are deliberately excluded:
# they catch bundled scripts/pipeline assets/reference implementations that
# are not "normative computer language definitions" in the 2.2.5 sense.
NORMDEF_EXTS = {".xsd", ".rng", ".rnc", ".dtd", ".wsdl", ".abnf", ".bnf",
                ".ebnf", ".g4", ".java", ".xml"}

# Illustrative-content and pipeline/asset directory names excluded from
# candidacy (case-insensitive): a heuristic proxy for "non-normative", not a
# semantic determination (see open_questions).
NORMDEF_EXCLUDE_DIRS = {
    "example", "examples", "sample", "samples", "test-case", "test-cases", "non-normative",
    "assets", "template", "templates", "_template", "_assets", "vendor", "css", "js", "dist", "build",
}

# Top-level README/index plain-text documentation: readme|index optionally
# followed by any number of '.'/'-'/'_'-separated segments (README.v1.2.txt,
# index.en-US.md, README-notes), so it is neither too narrow (missed multi-
# segment names) nor blind to a trailing binary extension (filtered below).
README_INDEX_RE = re.compile(r"(?i)^(?:readme|index)(?:[._-][\w-]+)*$")
NORMDEF_BINARY_DOC_EXTS = {".docx", ".doc", ".pdf", ".odt", ".zip", ".xlsx",
                           ".pptx", ".ppt", ".xls", ".png", ".jpg", ".jpeg", ".gif"}

# Structured reference-target extractors, run against raw (unnormalized)
# sibling/manifest/README text and the delivery item's own markdown/HTML.
NORMDEF_MD_TARGET_RE = re.compile(r"\]\((\S+?)\)")
NORMDEF_SCHEMALOC_RE = re.compile(r'(?:schemaLocation|location)\s*=\s*"([^"]+)"', re.I)
NORMDEF_JSONREF_RE = re.compile(r'"\$ref"\s*:\s*"([^"]+)"')


def _normdef_json_candidate(path: str) -> bool:
    """A JSON file counts as a normative-definition candidate when it
    declares a top-level $schema or $id key (reuses the registry's existing
    schema-id detection convention so the two checks agree on what is a
    schema)."""
    try:
        doc = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(doc, dict) and ("$schema" in doc or "$id" in doc)


def _normdef_collapse_dots(path: str) -> str:
    """Collapse './' and '../' path segments and a leading '/' (a same-
    package absolute-path reference), without needing os.path (which is
    filesystem-cwd-relative and the wrong tool for a URI path)."""
    out: list[str] = []
    for seg in path.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if out:
                out.pop()
            continue
        out.append(seg)
    return "/".join(out)


def _normdef_normalize_target(s: str) -> str:
    """Normalize an extracted link/src/import/schemaLocation/$ref target
    string for path-level comparison (algorithm step 7): strip query/
    fragment, percent-decode, Unicode NFC-normalize (macOS/APFS can hand
    back NFD filenames from os.walk while the same name typed into prose or
    an href is normally NFC -- a raw byte compare would silently miss the
    reference), unify path separators, and collapse './'/'../'/a leading
    '/' so a relative or same-package-absolute target string compares
    equal to the plain os.walk-derived candidate path."""
    s = s.split("?", 1)[0].split("#", 1)[0]
    s = urllib.parse.unquote(s)
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\\", "/")
    return _normdef_collapse_dots(s)


def _normdef_normalize_text(s: str) -> str:
    """Normalize a corpus TEXT BLOB (prose, not a single URL/path token) for
    token-boundary substring matching: percent-decode + Unicode NFC-
    normalize only. Deliberately does NOT strip a '?'/'#' suffix here --
    unlike a single target string, a text blob is free-form prose or file
    content that can legitimately contain '?' or '#' characters with no URL
    meaning at all (a question in the spec text, an XML comment, a Markdown
    heading marker); doing query/fragment surgery on a whole blob would
    truncate unrelated content instead of normalizing a URL."""
    return unicodedata.normalize("NFC", urllib.parse.unquote(s))


class _NormRefLinkParser(HTMLParser):
    """Collect href/src attribute target values and flattened visible text
    from a rendered HTML delivery item. Uses the stdlib parser (already
    imported for _AnchorParser) instead of an ad hoc regex so attribute-name
    case, whitespace around '=', and single/double/unquoted attribute values
    are all handled correctly, and a decoy 'data-href=...' attribute is
    never mistaken for a real href. <script>/<style> text is excluded from
    the visible-text pool."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.text_parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for key in ("href", "src"):
            v = d.get(key)
            if v:
                self.targets.append(v)
        if tag in ("script", "style"):
            self._skip += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.text_parts.append(data)

def check_normdef_refs(stage_dir: str, items: dict[str, str], md_text: str, html_text: str,
                       stage: str, f: Findings) -> None:
    """AC-PACKAGING-05 / TC Process 2.2.5: for a Standards Track Work Product,
    every separate plain-text file delivered to carry a normative computer
    language definition (schema, grammar, code, including fragments) must be
    referenced from somewhere in the Work Product -- the spec's own text, a
    sibling normative-definition file's own text (an xs:include/xs:import/
    wsdl:import/$ref chain), or the package's manifest.json or top-level
    README/index file. Standards Track only (csd, cs, os, errata, at any
    revision number); Non-Standards Track (cnd, cn) and unmapped stage
    tokens are not-applicable (open_questions #4). Illustrative examples/
    samples/test-cases/non-normative and pipeline/asset directories are
    excluded from candidacy; the package's own delivery artifacts,
    manifest.json (package root only), and *.css are never candidates
    themselves. Structured link/href/src/schemaLocation/$ref targets are
    extracted (not raw substring search) and matched at path level (full
    relative path or an unambiguous multi-component suffix) before falling
    back to a token-boundary basename match; a basename-only match among
    files sharing that basename in different directories cannot
    unambiguously resolve which file was referenced, so it WARNs instead of
    silently passing every tied file. Both the spec's own text and the
    rendered HTML are run through the tool's strip_code_blocks() first so an
    illustrative fenced/<pre>/<code> example naming a file is never counted
    as a real reference."""
    prefix_m = re.match(r"[a-z]+", stage)
    prefix = prefix_m.group(0) if prefix_m else stage
    if prefix not in STANDARDS_TRACK_PREFIXES:
        f.observe("normdef-refs", track=f"not-applicable (stage prefix '{prefix}')")
        return

    # Exclude the stage's own primary delivery artifacts by full package-
    # relative path (not bare basename): a sidecar in a different directory
    # that happens to share a delivery item's basename must still be
    # candidate-eligible. In practice this never collides with NORMDEF_EXTS
    # (delivery items are always md/html/pdf/docx/odt), but the check is
    # cheap and matches the spec's literal "the stage's own primary delivery
    # artifacts" wording rather than a name-only proxy for it.
    delivery_paths = {os.path.relpath(p, stage_dir).replace(os.sep, "/") for p in items.values()}

    candidates: list[str] = []
    for root, dirs, files in os.walk(stage_dir):
        dirs[:] = [d for d in dirs if d not in JUNK_DIRS and d.lower() not in NORMDEF_EXCLUDE_DIRS]
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, stage_dir).replace(os.sep, "/")
            if rel in delivery_paths or rel == "manifest.json" or name.lower().endswith(".css"):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in NORMDEF_EXTS or (ext == ".json" and _normdef_json_candidate(path)):
                candidates.append(rel)
    candidates.sort()
    f.observe("normdef-refs", candidates=candidates or "(none)")
    if not candidates:
        return
    candidate_set = set(candidates)

    # ---- reference corpus assembly (algorithm step 6) ---------------------
    # base_text/base_targets: the Work Product's own text (md source, or the
    # rendered HTML's visible text + href/src targets on the DOCX-native
    # track -- only one of the two per the already-established track
    # convention: is_word/md_text presence distinguishes the track, see
    # run()'s own `if md_text: ... ; if not md_text: (html path) ...`).
    base_text_parts: list[str] = []
    base_targets: set[str] = set()
    if md_text:
        stripped = strip_code_blocks(md_text, "md")
        base_text_parts.append(stripped)
        base_targets |= {_normdef_normalize_target(t)
                         for t in NORMDEF_MD_TARGET_RE.findall(stripped)}
    elif html_text:
        stripped = strip_code_blocks(html_text, "html")
        hp = _NormRefLinkParser()
        hp.feed(stripped)
        base_text_parts.append("".join(hp.text_parts))
        base_targets |= {_normdef_normalize_target(t) for t in hp.targets}

    # manifest.json (package root only -- a nested schemas/manifest.json is
    # left to normal JSON-candidate detection, not swallowed as "the"
    # manifest) and top-level README/index files, EXCLUDING any file that is
    # itself a normdef candidate (a candidate must not be able to satisfy
    # its own reference requirement merely by being folded into the shared
    # base corpus it is then tested against).
    mpath = os.path.join(stage_dir, "manifest.json")
    if os.path.isfile(mpath) and "manifest.json" not in candidate_set:
        try:
            mtext = read_text(mpath)
        except OSError:
            mtext = ""
        if mtext:
            base_text_parts.append(mtext)
            base_targets |= {_normdef_normalize_target(t) for t in NORMDEF_JSONREF_RE.findall(mtext)}
    for name in sorted(os.listdir(stage_dir)):
        p = os.path.join(stage_dir, name)
        if not os.path.isfile(p) or name in candidate_set or not README_INDEX_RE.match(name):
            continue
        if os.path.splitext(name)[1].lower() in NORMDEF_BINARY_DOC_EXTS:
            continue
        try:
            rtext = read_text(p)
        except OSError:
            continue
        base_text_parts.append(rtext)
        base_targets |= {_normdef_normalize_target(t) for t in NORMDEF_JSONREF_RE.findall(rtext)}
        base_targets |= {_normdef_normalize_target(t) for t in NORMDEF_SCHEMALOC_RE.findall(rtext)}

    base_text_norm = _normdef_normalize_text("\n".join(base_text_parts))

    # Sibling candidate files: each contributes its own raw text (for the
    # xs:include/xs:import/wsdl:import/$ref intra-definition reference, and
    # for plain basename mentions) and its own extracted targets, to every
    # OTHER candidate's corpus -- never to its own (a schema cannot satisfy
    # its own reference requirement by mentioning itself).
    sibling_content: dict[str, str] = {}
    sibling_targets: dict[str, set[str]] = {}
    for rel in candidates:
        try:
            text = read_text(os.path.join(stage_dir, rel))
        except OSError:
            text = ""
        sibling_content[rel] = text
        sibling_targets[rel] = {_normdef_normalize_target(t)
                                for t in (NORMDEF_SCHEMALOC_RE.findall(text)
                                          + NORMDEF_JSONREF_RE.findall(text))}

    basename_owners: dict[str, list[str]] = {}
    for rel in candidates:
        basename_owners.setdefault(os.path.basename(rel), []).append(rel)

    orphans, ambiguous = [], []
    for rel in candidates:
        base = os.path.basename(rel)
        rel_n = _normdef_normalize_target(rel)
        base_n = _normdef_normalize_target(base)

        other_targets = set(base_targets)
        for k, ts in sibling_targets.items():
            if k != rel:
                other_targets |= ts
        other_text_n = _normdef_normalize_text(
            "\n".join(v for k, v in sibling_content.items() if k != rel))
        corpus_text_n = base_text_norm + "\n" + other_text_n

        # (a) path-level match: the full relative path, or a path suffix of
        # it carrying 2+ components, appears as an extracted target --
        # unambiguous regardless of basename collisions elsewhere.
        parts = rel_n.split("/")
        path_forms = {rel_n} | {"/".join(parts[i:]) for i in range(1, len(parts))
                                if "/" in "/".join(parts[i:])}
        if path_forms & other_targets:
            continue

        # (b) basename fallback: the basename appears as an extracted
        # target's own basename, OR as a token-boundary literal substring
        # of the corpus's visible text (guards "widget.xsd.bak" from
        # satisfying "widget.xsd", and a raw substring search from being
        # fooled by a checksum/comment/longer-filename coincidence).
        target_basenames = {t.rsplit("/", 1)[-1] for t in other_targets}
        token_pat = re.compile(r"(?<![\w.-])" + re.escape(base_n) + r"(?![\w.-])")
        matched = base_n in target_basenames or bool(token_pat.search(corpus_text_n))
        if not matched:
            orphans.append(rel)
        elif len(basename_owners[base]) > 1:
            ambiguous.append(rel)
        # else: unambiguous basename match, PASS

    f.observe("normdef-refs", orphans=len(orphans), ambiguous_basename_only=len(ambiguous))
    for rel in sorted(ambiguous):
        f.add(WARN, "normdef-refs",
              f"{rel}: basename-only reference cannot be unambiguously resolved among files "
              f"sharing the basename '{os.path.basename(rel)}'; confirm and use path-qualified "
              f"references (TC Process 2.2.5: 'Each text file must be referenced from the Work "
              f"Product; and').")
    for rel in sorted(orphans):
        f.add(BLOCKER, "normdef-refs",
              f"{rel}: normative-definition file is never referenced from the Work Product "
              f"(TC Process 2.2.5: 'Each text file must be referenced from the Work Product; "
              f"and').")


# ===== AC-PACKAGING-17 (uri-alias) =====
# AC-PACKAGING-17: Naming Directives v1.7 s6.5 URI Aliases, three prongs
# ((a) META-refresh, (b) byte-identical duplicate files, (c) canonical-URI
# citations routed through a redirect/URL-shortening domain), scoped to the
# single stage/revision package directory under validation (s5.2's
# "published instance"). That scope boundary structurally excludes the
# corpus's one documented authorized alias (the Latest-stage URI, which s5.2
# confirms is addressed via a location outside any single stage-specific
# package), so this check never has to detect or special-case it.
#
# Hardened at FIXER pass against independent-verifier + adversary findings:
# gate the HTML-track prose scan to the DOCX-native track only (a normal
# md-track package's html_text is a re-rendering of the SAME prose, not
# independent material -- scanning both double-counted every real hit);
# excise the This/Previous/Latest-stage and Related-Work zones from BOTH
# prose scans (front-matter/cover-block checks already own those, and
# Related Work is out of scope entirely) so the generic scan cannot
# re-flag content a dedicated check already owns or a bibliography entry
# never claiming to be an OASIS resource; replace the brittle <a href="...">
# regex with an HTMLParser-based extractor (handles quote styles, unquoted
# attributes, whitespace, entity decoding, code-block skipping in one
# pass); classify prong (b) severity by exact package-relative path
# membership instead of basename, closing a false-escalation path where an
# unrelated ancillary file coincidentally shares a delivery item's
# basename in a different directory; and guard every filesystem/JSON read
# against a malformed or racing package so the check WARNs/skips rather
# than raising.

URI_ALIAS_REDIRECT_DOMAINS = {
    "tinyurl.com", "bit.ly", "goo.gl", "ow.ly", "t.co", "is.gd", "buff.ly",
    "rebrand.ly", "tiny.cc", "cutt.ly", "shorturl.at", "rb.gy", "purl.oclc.org",
}

# "docs.oasis-open.org" already contains "oasis-open.org" as a substring, so
# a single case-insensitive search for "oasis-open.org" covers both literal
# strings the spec names for the scope-gate(ii) anchor-text/sentence test.
URI_ALIAS_CANONICAL_SUBSTR_RE = re.compile(r"oasis-open\.org", re.IGNORECASE)

URI_ALIAS_BARE_URL_RE = re.compile(r"https?://\S+?(?=[)\s\\]|$)")
# Widened at FIXER pass: optional angle-bracket destination and an optional
# "title"/'title' after the URL (both valid CommonMark inline-link forms);
# reference-style [text][ref] links are still out of scope, matching every
# other link-aware check already in this file (check_md_links,
# check_correction_classes' link-mismatch) -- no precedent for resolving
# them exists anywhere in the tool, so this stays consistent rather than
# inventing a first one here.
URI_ALIAS_MD_LINK_RE = re.compile(
    r"\[([^\]]+)\]\(\s*<?([^\s)>]+)>?(?:\s+\"[^\"]*\"|\s+'[^']*')?\s*\)")
# A sentence terminator only counts when followed by whitespace/end (so the
# dots inside a bare domain name like "oasis-open.org" are never misread as
# sentence boundaries and truncate the window before the substring itself).
URI_ALIAS_SENT_BOUND_RE = re.compile(r"[.!?](?=\s|$)|\n\s*\n")
URI_ALIAS_NOISE_FLOOR_BYTES = 16


class _MetaRefreshParser(HTMLParser):
    """Prong (a): detect a live <meta http-equiv=refresh> tag. HTMLParser
    already never re-parses comment content as tags, and treats <script>/
    <style> as CDATA content elements automatically; <pre>/<code>/<template>
    are tracked explicitly here so a spec's own worked "what not to do"
    example (shown verbatim, unescaped, inside one of those) does not read
    as a live tag (hardened per the false_positive_risks entry for prong a)."""

    _SKIP_TAGS = {"pre", "code", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found = False
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "meta":
            d = {k.lower(): (v or "") for k, v in attrs}
            if d.get("http-equiv", "").strip().lower() == "refresh":
                self.found = True

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1


class _AliasProseParser(HTMLParser):
    """Prong (c) HTML-track prose extractor (FIXER pass replacement for the
    original regex-based <a href="..."> matcher, which missed href='...',
    unquoted attributes, and whitespace around '='). Collects every live
    <a>'s (href, visible-text) pair and the flattened non-anchor body text
    in one pass, with <pre>/<code>/<template> content excluded from both
    (mirrors _MetaRefreshParser's skip-tag handling) and HTML entities
    already decoded (HTMLParser convert_charrefs=True) -- this closes the
    adversary's html-anchors, html-entity-decoding, and html-code-examples
    findings together instead of three separate regex patches. A
    tag-boundary (any non-anchor start/end tag) inserts a paragraph break
    into the flattened text rather than a bare space, so the sentence-
    window guard (see _uri_alias_sentence_window) has a real boundary to
    stop at between block elements -- the original single-space join let a
    docs.oasis-open.org mention in one <p> leak into a redirect URL's
    "sentence" in a neighboring <p> with no punctuation between them."""

    _SKIP_TAGS = {"pre", "code", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list = []
        self.flat_parts: list = []
        self._stack: list = []
        self._anchor_href = ""
        self._anchor_text: list = []

    def _skipping(self) -> bool:
        return any(t in self._SKIP_TAGS for t in self._stack)

    def handle_starttag(self, tag, attrs):
        self._stack.append(tag)
        if self._skipping():
            return
        if tag == "a" and self._stack.count("a") == 1:
            d = {k.lower(): (v or "") for k, v in attrs}
            self._anchor_href = d.get("href", "")
            self._anchor_text = []
        if "a" not in self._stack:
            self.flat_parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag == "a" and "a" in self._stack:
            self.anchors.append((self._anchor_href, "".join(self._anchor_text).strip()))
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i] == tag:
                del self._stack[i]
                break
        if not self._skipping() and "a" not in self._stack:
            self.flat_parts.append("\n\n")

    def handle_data(self, data):
        if self._skipping():
            return
        if "a" in self._stack:
            self._anchor_text.append(data)
        else:
            self.flat_parts.append(data)

    @property
    def flat_text(self) -> str:
        return "".join(self.flat_parts)


def _uri_alias_is_redirect_domain(url: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower().split("@")[-1].split(":")[0]
    host = host.rstrip(".")  # DNS root dot: bit.ly. is the same host as bit.ly
    if host.startswith("www."):
        host = host[4:]
    return any(host == d or host.endswith("." + d) for d in URI_ALIAS_REDIRECT_DOMAINS)


def _uri_alias_manifest_citable_paths(stage_dir: str) -> set:
    """Package-relative paths the package's own manifest.json (if any) labels
    authoritative or delivery: a duplicate that also lands at one of these
    paths is a genuinely citable canonical resource for prong (b)'s
    severity split (algorithm step 5), not an incidental ancillary
    duplicate. Guarded at every level (missing file, malformed JSON,
    non-object root, non-list items, non-object entry, non-string path) so
    a malformed manifest is simply not consulted, never a crash."""
    mpath = os.path.join(stage_dir, "manifest.json")
    if not os.path.isfile(mpath):
        return set()
    try:
        man = json.loads(read_text(mpath))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(man, dict):
        return set()
    items = man.get("items")
    if not isinstance(items, list):
        return set()
    out = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("role") not in ("authoritative", "delivery"):
            continue
        path = item.get("path")
        if isinstance(path, str) and path:
            out.add(os.path.normpath(path))
    return out


def _uri_alias_cover_block_urls(html_text: str, start_pat: str, end_pats: list) -> list:
    """Every URL (any host) in a labelled DOCX-native cover-page block.
    Reuses the same locate-<body>/strip-tags/collapse-whitespace/slice
    technique check_html_cover's own cover-text extraction applies, but does
    not filter to docs.oasis-open.org the way that function's private
    urls_between() closure does: a redirect-service URL is exactly the
    off-domain case this prong exists to catch, and check_html_cover's
    closure is not itself an exposed, reusable module-level helper. FIXER
    pass addition: also re-runs the same start/end label search directly
    against the RAW (tag-bearing) slice to pull href="..." values -- a
    cover field rendered as <a href="...">This version</a> would otherwise
    lose its URL entirely when tags are stripped before the search, since
    only the anchor's visible text (if any) would survive. The label
    regex still matches correctly against the raw slice because the label
    wording is plain text even when wrapped in inline markup."""
    body_at = html_text.find("<body")
    cover = html_text[body_at if body_at >= 0 else 0:][:120000]
    head = re.sub(r"<[^>]+>", " ", cover)
    head = re.sub(r"&nbsp;|&#160;|\s+", " ", head)
    urls: list = []
    m = re.search(start_pat, head, re.I)
    if m:
        seg = head[m.end():]
        cut = len(seg)
        for e in end_pats:
            m2 = re.search(e, seg, re.I)
            if m2:
                cut = min(cut, m2.start())
        urls.extend(re.findall(r"https?://\S+", seg[:cut]))
    m3 = re.search(start_pat, cover, re.I)
    if m3:
        segc = cover[m3.end():]
        cutc = len(segc)
        for e in end_pats:
            m4 = re.search(e, segc, re.I)
            if m4:
                cutc = min(cutc, m4.start())
        urls.extend(re.findall(r'href\s*=\s*["\']([^"\']+)["\']', segc[:cutc]))
    return urls


def _uri_alias_sentence_window(text: str, start: int, end: int) -> str:
    """The prose window around a bare URL, bounded by the nearest sentence
    terminator or paragraph break on either side (algorithm step 6/9, added
    at RED2): kept sentence-scoped, not paragraph- or document-scoped, so a
    document's own front-matter boilerplate mentioning docs.oasis-open.org
    cannot leak into an unrelated sentence and cause a false match."""
    left = 0
    for m in URI_ALIAS_SENT_BOUND_RE.finditer(text[:start]):
        left = m.end()
    right = len(text)
    m2 = URI_ALIAS_SENT_BOUND_RE.search(text[end:])
    if m2:
        right = end + m2.start() + 1
    return text[left:right]


def _uri_alias_excise_md_sections(text: str, heading_pats: list) -> str:
    """Blank the body of each named markdown heading section (from the
    heading's own line through the next '#+' heading or the end of the
    document) before the generic prose scan sees the text -- FIXER-pass
    generalization of the previous Related-Work-only excision to also cover
    This/Previous/Latest-Stage: algorithm step 9(a) requires suppressing a
    prong-(c) match inside a This/Latest block (the front-matter check
    already BLOCKERs any non-canonical URL there) and, independently, the
    dedicated Previous-stage loop above already owns that block on its own
    -- scanning it again here would double-count the same physical redirect
    citation. Unlike the tool's other Related-Work excision (see
    check_front_matter), this also closes cleanly when the named section is
    the LAST one in the document (no trailing heading to match against)."""
    out = text
    for pat in heading_pats:
        m = re.search(pat + r".*?$", out, re.M | re.I)
        if not m:
            continue
        rest = out[m.end():]
        nxt = re.search(r"^#+ ", rest, re.M)
        section_end = m.end() + (nxt.start() if nxt else len(rest))
        blanked = "\n" * out[m.end():section_end].count("\n")
        out = out[:m.end()] + blanked + out[section_end:]
    return out


def _uri_alias_excise_html_noise_zones(html_text: str) -> str:
    """Blank (1) the DOCX-native cover-field label zone (This-version
    through the Technical-Committee/Chairs boundary that closes the cover
    block) and (2) any Related-Work section (heading through the next H1-H6
    tag or end of document) before the generic HTML prose scan sees the
    text. Zone (1) already has its own dedicated redirect-domain check
    (_uri_alias_cover_block_urls) -- reproduced directly at FIXER pass: a
    cover rendered as adjacent <p> blocks with no sentence punctuation
    between them collapses to one unbounded "sentence" once tags are
    stripped, so a Latest-version field's docs.oasis-open.org text leaked
    into a This-version redirect URL's window and double-fired. Zone (2) is
    the HTML-track half of the corpus's Related-Work false-positive guard,
    which the original implementation only ever applied on the markdown
    track. Heading labels are matched directly against the raw (tag-
    bearing) HTML on the same 'label wording is plain text even inside
    inline markup' basis _uri_alias_cover_block_urls already relies on; a
    missing label leaves that zone untouched."""
    out = html_text
    m = re.search(r"This (version|stage)", out, re.I)
    if m:
        rest = out[m.start():]
        m2 = re.search(r"Chairs?\b|Technical Committee", rest, re.I)
        end = m.start() + (m2.end() if m2 else min(len(rest), 6000))
        out = out[:m.start()] + (" " * (end - m.start())) + out[end:]
    m3 = re.search(r"Related [Ww]ork", out, re.I)
    if m3:
        rest2 = out[m3.end():]
        m4 = re.search(r"<h[1-6][^>]*>", rest2, re.I)
        end2 = m3.end() + (m4.start() if m4 else len(rest2))
        out = out[:m3.start()] + (" " * (end2 - m3.start())) + out[end2:]
    return out


def _uri_alias_scan_md_prose(prose: str, f: Findings) -> None:
    """Prong (c) plain-prose gate on the markdown body (This/Previous/
    Latest-Stage and Related-Work already excised by the caller). A
    [shown](target) construct whose shown text is itself a URL is left
    entirely to the existing link-mismatch check (which already BLOCKERs
    any shown!=target pair regardless of domain) -- skipped here per
    algorithm step 9(b) so the two checks do not double-count the same
    bracketed-link defect."""
    bare_source = prose
    link_matches = list(URI_ALIAS_MD_LINK_RE.finditer(prose))
    for m in link_matches:
        shown, target = m.group(1).strip(), m.group(2).rstrip(".,)>")
        bare_source = bare_source[:m.start()] + (" " * (m.end() - m.start())) + bare_source[m.end():]
        if re.match(r"^<?https?://", shown, re.I):
            continue
        if _uri_alias_is_redirect_domain(target) and URI_ALIAS_CANONICAL_SUBSTR_RE.search(shown):
            f.add(BLOCKER, "uri-alias",
                  f"Anchor text '{shown}' names oasis-open.org but links to a "
                  f"redirect/URL-shortening domain: {target}. Naming Directives "
                  f"v1.7 s6.5(c) bars constructing citations to canonical OASIS "
                  f"resources via a redirect/shortening service.")
    bare_matches = list(URI_ALIAS_BARE_URL_RE.finditer(bare_source))
    f.observe("uri-alias",
              prong_c_md_anchor_links_scanned=len(link_matches),
              prong_c_md_bare_urls_scanned=len(bare_matches))
    for m in bare_matches:
        url = m.group(0).rstrip(".,)")
        if not _uri_alias_is_redirect_domain(url):
            continue
        window = _uri_alias_sentence_window(bare_source, m.start(), m.end())
        if URI_ALIAS_CANONICAL_SUBSTR_RE.search(window):
            f.add(BLOCKER, "uri-alias",
                  f"Prose cites oasis-open.org while linking a redirect/URL-"
                  f"shortening domain in the same sentence: {url}. Naming "
                  f"Directives v1.7 s6.5(c).")


def _uri_alias_scan_html_prose(html_text: str, f: Findings) -> None:
    """Prong (c) plain-prose gate on rendered HTML body text (DOCX-native
    track only -- the caller gates this to `not md_text`; This/Previous/
    Latest cover fields and Related Work already excised by the caller).
    FIXER pass: rebuilt on _AliasProseParser instead of a regex <a> match
    plus a second tag-stripping pass, so anchor extraction, code-block
    skipping, and entity decoding happen once, consistently, in document
    order."""
    parser = _AliasProseParser()
    try:
        parser.feed(strip_code_blocks(html_text, "html"))
    except Exception:  # noqa: BLE001 - malformed HTML WARNs elsewhere, not here
        return
    flat = parser.flat_text
    bare_matches = list(URI_ALIAS_BARE_URL_RE.finditer(flat))
    f.observe("uri-alias",
              prong_c_html_anchor_links_scanned=len(parser.anchors),
              prong_c_html_bare_urls_scanned=len(bare_matches))
    for target, shown in parser.anchors:
        if not target:
            continue
        if re.match(r"^<?https?://", shown, re.I):
            continue
        if _uri_alias_is_redirect_domain(target) and URI_ALIAS_CANONICAL_SUBSTR_RE.search(shown):
            f.add(BLOCKER, "uri-alias",
                  f"Anchor text '{shown}' names oasis-open.org but links to a "
                  f"redirect/URL-shortening domain: {target}. Naming Directives "
                  f"v1.7 s6.5(c) bars constructing citations to canonical OASIS "
                  f"resources via a redirect/shortening service.")
    for m in bare_matches:
        url = m.group(0).rstrip(".,)")
        if not _uri_alias_is_redirect_domain(url):
            continue
        window = _uri_alias_sentence_window(flat, m.start(), m.end())
        if URI_ALIAS_CANONICAL_SUBSTR_RE.search(window):
            f.add(BLOCKER, "uri-alias",
                  f"Prose cites oasis-open.org while linking a redirect/URL-"
                  f"shortening domain in the same sentence: {url}. Naming "
                  f"Directives v1.7 s6.5(c).")

def check_uri_alias(stage_dir: str, items: dict, md_text: str, html_text: str,
                    f: Findings) -> None:
    """AC-PACKAGING-17: Naming Directives v1.7 s6.5 URI Aliases. Scoped to
    the single stage/revision package directory under validation (s5.2's
    "published instance"), which structurally excludes the corpus's one
    documented authorized alias (the Latest-stage alias -- see
    severity_rationale in the spec record). Three prongs:
      (a) a live <meta http-equiv=refresh> element in any delivered HTML file;
      (b) two package-relative paths carrying byte-identical content --
          BLOCKER only when a stage-root delivery file or manifest-cited
          file is in the bucket (by exact relative path, not name
          coincidence), WARN for any other ancillary duplicate;
      (c) a canonical-OASIS-resource citation routed through a known
          redirect/URL-shortening domain, gated to a This/Previous/Latest
          front-matter block (or its DOCX-native cover-page equivalent) or
          to plain-prose anchor text / a bare URL's enclosing sentence that
          literally names oasis-open.org. The HTML-track prose scan and the
          DOCX-native cover extraction only run when there is no md
          source (`not md_text`): for an md-track package, html_text is a
          rendering of the SAME prose md_text already covers, and scanning
          both double-counts every real hit. This/Latest/Related-Work
          blocks (md) and the cover-field zone/Related-Work (html) are
          excised before the generic prose scan so it cannot re-flag
          content a dedicated check already owns (front-matter, the
          Previous-stage loop below, or the cover-block loop below); a
          [shown-url](target-url) construct is left to the existing
          link-mismatch check. See duplicates_existing in the spec record
          for the full accounting."""
    delivery_paths = {os.path.normpath(os.path.relpath(p, stage_dir))
                       for p in items.values() if isinstance(p, str)}

    # ---- prong (a): META-refresh -------------------------------------------
    html_files = sorted(
        os.path.join(r, n) for r, _d, fs in os.walk(stage_dir) for n in fs
        if os.path.splitext(n)[1].lower() in (".html", ".htm", ".xhtml"))
    f.observe("uri-alias", prong_a_html_files_scanned=len(html_files))
    for p in html_files:
        rel = os.path.relpath(p, stage_dir)
        try:
            body = read_text(p)
        except OSError:
            continue
        parser = _MetaRefreshParser()
        try:
            parser.feed(body)
        except Exception:  # noqa: BLE001 - a malformed HTML file WARNs elsewhere, not here
            continue
        if parser.found:
            f.add(BLOCKER, "uri-alias",
                  f'{rel}: contains a live <meta http-equiv="refresh"> element. '
                  f"Naming Directives v1.7 s6.5(a) bars unauthorized URI "
                  f"aliasing via META-refresh elements.")

    # ---- prong (b): duplicate content --------------------------------------
    manifest_paths = _uri_alias_manifest_citable_paths(stage_dir)
    citable_paths = delivery_paths | manifest_paths
    stage_abs = os.path.realpath(stage_dir)
    digests: dict = {}
    unreadable = 0
    for root, _dirs, names in os.walk(stage_dir):
        for name in names:
            p = os.path.join(root, name)
            rel = os.path.relpath(p, stage_dir)
            try:
                if os.path.islink(p):
                    target = os.path.realpath(p)
                    if not os.path.isfile(target):
                        continue  # dangling: not this check's concern (false_negative_risks)
                    try:
                        if os.path.commonpath([stage_abs, target]) != stage_abs:
                            continue  # off-package target: not chased (false_negative_risks)
                    except ValueError:
                        continue
                    digest = sha256_file(target)
                elif os.path.isfile(p):
                    digest = sha256_file(p)
                else:
                    continue
            except OSError:
                unreadable += 1
                continue  # a racing/unreadable entry WARNs nowhere else; skip, don't crash
            digests.setdefault(digest, []).append(rel)
    f.observe("uri-alias",
              prong_b_files_hashed=sum(len(v) for v in digests.values()),
              prong_b_duplicate_buckets=sum(1 for v in digests.values() if len(v) > 1),
              prong_b_unreadable_entries_skipped=unreadable)
    for digest, paths in sorted(digests.items()):
        if len(paths) < 2:
            continue
        try:
            size = os.path.getsize(os.path.join(stage_dir, paths[0]))
        except OSError:
            size = URI_ALIAS_NOISE_FLOOR_BYTES + 1  # can't verify: don't silently drop a real dup
        if size < URI_ALIAS_NOISE_FLOOR_BYTES:
            continue
        normalized_paths = {os.path.normpath(p) for p in paths}
        listing = ", ".join(sorted(paths))
        if normalized_paths & citable_paths:
            f.add(BLOCKER, "uri-alias",
                  f"Byte-identical content under {len(paths)} different paths, "
                  f"including a delivery/manifest-cited file ({listing}): Naming "
                  f"Directives v1.7 s6.5(b) bars preparing files with identical "
                  f"content under two different filenames within a published "
                  f"instance.")
        else:
            f.add(WARN, "uri-alias",
                  f"Byte-identical content under {len(paths)} different paths, "
                  f"none of which is a delivery/manifest-cited file ({listing}): "
                  f"an ancillary duplicate, not a citable-resource aliasing risk "
                  f"under s6.5(b) unless it later becomes citable.")

    # ---- prong (c): redirect/shortener domain citations --------------------
    this_urls = stage_urls_from_md(md_text, "This") if md_text else []
    prev_urls = stage_urls_from_md(md_text, "Previous") if md_text else []
    latest_urls = stage_urls_from_md(md_text, "Latest") if md_text else []
    f.observe("uri-alias",
              prong_c_md_block_urls_scanned=len(this_urls) + len(prev_urls) + len(latest_urls))
    # This/Latest-stage block matches are already caught by the existing
    # front-matter "Stage URL is not under docs.oasis-open.org" check (any
    # non-canonical URL there, redirect-service or not) -- algorithm step
    # 9(a); only the Previous-stage block is genuinely uncovered elsewhere.
    for u in prev_urls:
        if _uri_alias_is_redirect_domain(u):
            f.add(BLOCKER, "uri-alias",
                  f"Previous-stage front-matter cites a redirect/URL-shortening "
                  f"domain instead of the canonical resource: {u.rstrip('.,)')}")

    if not md_text and html_text:
        # DOCX-native cover: check_html_cover only extracts docs.oasis-open.org
        # -scoped URLs, so a redirect-domain cover citation is not caught by
        # any existing check at all (genuinely uncovered surface).
        cover_urls = (
            _uri_alias_cover_block_urls(
                html_text, r"This (version|stage)",
                [r"Previous (version|stage)", r"Latest (version|stage)", r"Technical Committee"])
            + _uri_alias_cover_block_urls(
                html_text, r"Previous (version|stage)",
                [r"Latest (version|stage)", r"Technical Committee"])
            + _uri_alias_cover_block_urls(
                html_text, r"Latest (version|stage)",
                [r"Technical Committee", r"Chairs?\b"]))
        cover_urls = list(dict.fromkeys(cover_urls))  # de-dupe (text+href can name the same URL)
        f.observe("uri-alias", prong_c_docx_cover_urls_scanned=len(cover_urls))
        for u in cover_urls:
            if _uri_alias_is_redirect_domain(u):
                f.add(BLOCKER, "uri-alias",
                      f"DOCX-native cover field cites a redirect/URL-shortening "
                      f"domain instead of the canonical resource: {u.rstrip('.,)')}")

        # DOCX-native track only: the rendered body is the full document, so
        # the cover-field zone (owned by the loop above) and any Related
        # Work section (out of scope, see false_positive_risks) are excised
        # first -- otherwise both are re-scored by the generic scan below.
        _uri_alias_scan_html_prose(_uri_alias_excise_html_noise_zones(html_text), f)

    # md-track plain-prose anchor text / bare-URL citations. This/Previous/
    # Latest-stage and Related Work are excised first: This/Latest are the
    # front-matter check's territory (step 9(a)); Previous is the dedicated
    # loop's territory just above (scanning it again here would double-count
    # the same physical redirect citation); a legitimate third-party
    # citation in Related Work is not claiming to be an OASIS resource and
    # is not this check's business.
    if md_text:
        prose = strip_code_blocks(md_text, "md")
        prose = _uri_alias_excise_md_sections(
            prose,
            [r"^#+ This (?:Stage|Version)\b",
             r"^#+ Previous (?:Stage|Version)\b",
             r"^#+ Latest (?:Stage|Version)\b",
             r"^#+ Related [Ww]ork\b"])
        _uri_alias_scan_md_prose(prose, f)


# ===== AC-PACKAGING-20 (xml-namespace) =====
import xml.etree.ElementTree as ET

# Naming Directives s3+s8: the xxxx segment of an http(s) namespace name may
# use only alphanumerics plus '.', '-', and internal '/', terminating in '/',
# '#', or an alphanumeric -- explicitly excluding '_'.
XML_NS_TAIL_XXXX = r"[A-Za-z0-9.\-/]*[A-Za-z0-9/#]"

# Conventional non-normative directories: illustrative/example/vendored/
# interop schema files legitimately declare non-canonical namespaces and are
# out of scope unless the package manifest marks the file normative.
XML_NS_EXCLUDED_DIRS = {"test-cases", "examples", "samples", "third-party", "vendor", "interop"}

# Naming Directives s8: URN-based namespaces are permitted only for TCs that
# already used the feature pre-2012, or associated Maintenance Activity TCs,
# "where architectural considerations require continued use of URNs" --
# approved by Project Administration. Maintained externally; extend as PA
# approves additional TCs (open question: who owns/maintains this list).
XML_NS_URN_GRANDFATHER_TCS = frozenset({"ubl"})

# Naming Directives v1.2 s9: pre-2012 practice on the OLD
# http://docs.oasis-open.org/ns/[tc-shortname]/... pattern "may be
# grandfathered, if approved by Project Administration". True = PA approval
# is machine-confirmable at check time (clean pass); False = the TC is on
# record as grandfathered but approval cannot be machine-confirmed (WARN).
# Maintained externally alongside XML_NS_URN_GRANDFATHER_TCS. The bypass
# below only ever applies to a namespace still hosted at docs.oasis-open.org
# -- the pre-2012 practice being grandfathered is an OLD PATH SHAPE on that
# same host (docs.oasis-open.org/ns/[tc]/... instead of the current
# [tc]/ns/xxxx pattern), never a license to declare an unrelated domain.
# See _xml_ns_grandfather_eligible.
XML_NS_PATTERN_GRANDFATHER_TCS: dict = {"cmis": True}


def _xml_ns_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_ns_scheme(uri: str) -> str:
    return urllib.parse.urlsplit(uri).scheme.lower()


def _xml_ns_grandfather_eligible(ns: str) -> bool:
    """The pattern-grandfather allowance only ever covers the pre-2012
    docs.oasis-open.org/ns/[tc-shortname]/... path SHAPE on the OASIS docs
    host itself -- it is not a blanket bypass for any mismatched namespace a
    listed TC happens to declare, which could otherwise be an unrelated
    domain entirely."""
    tail = ns.split("://", 1)[-1]
    host = tail.split("/", 1)[0].lower()
    return host == "docs.oasis-open.org"


def _xml_ns_under_excluded_dir(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")[:-1]
    return any(p.lower() in XML_NS_EXCLUDED_DIRS for p in parts)


def _xml_ns_manifest_normative(stage_dir: str) -> set:
    mpath = os.path.join(stage_dir, "manifest.json")
    if not os.path.isfile(mpath):
        return set()
    try:
        man = json.loads(read_text(mpath))
    except (json.JSONDecodeError, OSError):
        return set()
    if not isinstance(man, dict):
        return set()
    items_field = man.get("items")
    if not isinstance(items_field, list):
        return set()
    out = set()
    for item in items_field:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if item.get("normative") and isinstance(path, str) and path:
            out.add(os.path.normpath(path))
    return out

def check_xml_namespaces(stage_dir: str, base_this_stage: str, f: Findings) -> None:
    """AC-PACKAGING-20: every namespace a shipped .xsd/.wsdl/.rng formally
    declares as its OWN (targetNamespace / root ns) must be an
    http(s)://docs.oasis-open.org/[tc-shortname]/ns/xxxx URI (consistent
    scheme package-wide) or a urn: on the grandfather allowlist. Namespaces
    merely imported/referenced are out of scope; only self-declared ones are
    pulled.

    Called from run() as check_xml_namespaces(stage_dir, base, f), reusing
    the This-Stage base URL that check_front_matter/check_html_cover already
    resolved into `base` earlier in run() -- the same variable check_schemas
    and check_revision_collision already consume (`base` is in scope for the
    whole output-suite block of run(), not just the two named callers)."""
    tc_shortname = ""
    if base_this_stage.startswith(SITE + "/"):
        tc_shortname = base_this_stage[len(SITE) + 1:].split("/", 1)[0].lower()

    normative_override = _xml_ns_manifest_normative(stage_dir)
    candidates = []
    excluded = 0
    for root_dir, _dirs, files in os.walk(stage_dir):
        for name in files:
            ext = os.path.splitext(name)[1].lstrip(".").lower()
            if ext not in ("xsd", "wsdl", "rng"):
                continue
            path = os.path.join(root_dir, name)
            rel = os.path.relpath(path, stage_dir)
            if _xml_ns_under_excluded_dir(rel) and os.path.normpath(rel) not in normative_override:
                excluded += 1
                continue
            candidates.append((path, rel, ext))
    f.observe("xml-namespace", schema_files_scanned=len(candidates),
              schema_files_excluded=excluded,
              tc_shortname=tc_shortname or "(unresolved: no this-stage URL)")
    if not candidates:
        return

    declared: list = []  # (namespace_uri, source_rel, kind)
    parse_failures: list = []
    for path, rel, ext in sorted(candidates):
        try:
            root = ET.parse(path).getroot()
        except Exception:
            # A separate integrity/well-formedness check owns malformed XML;
            # this check only records that it could not be evaluated.
            parse_failures.append(rel)
            continue
        if ext == "xsd":
            if _xml_ns_local(root.tag) == "schema":
                ns = root.get("targetNamespace")
                if ns:
                    declared.append((ns, rel, "xsd"))
        elif ext == "wsdl":
            root_local = _xml_ns_local(root.tag)
            if root_local in ("definitions", "description"):
                # "definitions" = WSDL 1.1 root; "description" = WSDL 2.0
                # root -- both carry the reserved targetNamespace attribute.
                ns = root.get("targetNamespace")
                if ns:
                    declared.append((ns, rel, "wsdl" if root_local == "definitions" else "wsdl2"))
            for types_el in root.iter():
                if _xml_ns_local(types_el.tag) != "types":
                    continue
                for schema_el in types_el.iter():
                    if _xml_ns_local(schema_el.tag) == "schema":
                        ns2 = schema_el.get("targetNamespace")
                        if ns2:
                            declared.append((ns2, rel, "wsdl-embedded"))
        elif ext == "rng":
            if _xml_ns_local(root.tag) in ("grammar", "element"):
                root_ns = root.get("ns") or ""
                if root_ns:
                    declared.append((root_ns, rel, "rng"))
                for el in root.iter():
                    if el is root:
                        continue
                    other = el.get("ns")
                    if other and other != root_ns:
                        f.add(WARN, "xml-namespace",
                              f"{rel}: possible additional RELAX NG namespace '{other}' not "
                              f"evaluated by this check -- manual review (root ns is "
                              f"'{root_ns or '(none)'}').")
                        break

    f.observe("xml-namespace",
              namespaces_declared=sorted({ns for ns, _rel, _kind in declared}) or "(none)",
              parse_failures=sorted(parse_failures) or "(none)")

    # ---- pattern + URN checks: both need a resolved tc-shortname ----------
    if tc_shortname:
        pattern_re = re.compile(
            rf"^docs\.oasis-open\.org/{re.escape(tc_shortname)}/ns/{XML_NS_TAIL_XXXX}$")
        pattern_seen = set()
        for ns, rel, _kind in declared:
            if _xml_ns_scheme(ns) not in ("http", "https"):
                continue
            tail = ns.split("://", 1)[-1]
            if pattern_re.match(tail):
                continue
            if ns in pattern_seen:
                continue
            pattern_seen.add(ns)
            grand = XML_NS_PATTERN_GRANDFATHER_TCS.get(tc_shortname)
            if grand is not None and not _xml_ns_grandfather_eligible(ns):
                # Listed TC, but this namespace is not even a docs.oasis-open.org
                # URI: the pre-2012 path-shape grandfather does not extend to an
                # unrelated domain, so fall through to the ordinary BLOCKER path.
                grand = None
            if grand is True:
                continue
            if grand is False:
                f.add(WARN, "xml-namespace",
                      f"{rel}: namespace '{ns}' does not match the "
                      f"{tc_shortname}/ns/xxxx pattern (Naming Directives s8), but "
                      f"'{tc_shortname}' is recorded as a pre-2012 pattern grandfather "
                      f"whose Project Administration approval cannot be machine-confirmed "
                      f"at check time. Confirm approval or align the namespace with the "
                      f"current pattern.")
            else:
                f.add(BLOCKER, "xml-namespace",
                      f"{rel}: namespace '{ns}' does not match the required "
                      f"http(s)://docs.oasis-open.org/{tc_shortname}/ns/xxxx pattern "
                      f"(Naming Directives s8).")

        urn_seen = set()
        for ns, rel, _kind in declared:
            if _xml_ns_scheme(ns) != "urn":
                continue
            if tc_shortname in XML_NS_URN_GRANDFATHER_TCS:
                continue
            if ns in urn_seen:
                continue
            urn_seen.add(ns)
            f.add(BLOCKER, "xml-namespace",
                  f"{rel}: namespace '{ns}' uses a urn: scheme, but '{tc_shortname}' is "
                  f"not on the URN-grandfather allowlist. Naming Directives s8: "
                  f"URN-based namespaces 'must not be declared otherwise, since they "
                  f"lack a standard, ubiquitous resolution method using DNS[+HTTP].'")

    # ---- scheme-consistency check: whole package, no tc-shortname needed --
    tail_map = {}
    for ns, rel, _kind in declared:
        scheme = _xml_ns_scheme(ns)
        if scheme not in ("http", "https"):
            continue
        tail_map.setdefault(ns.split("://", 1)[-1], []).append((scheme, ns, rel))
    for tail, entries in sorted(tail_map.items()):
        schemes = {e[0] for e in entries}
        if len(schemes) < 2:
            continue
        http_e = next(e for e in entries if e[0] == "http")
        https_e = next(e for e in entries if e[0] == "https")
        f.add(BLOCKER, "xml-namespace",
              f"Namespace tail '{tail}' is declared under both http and https scheme "
              f"within the same package: {http_e[2]} declares '{http_e[1]}', "
              f"{https_e[2]} declares '{https_e[1]}'. Naming Directives s8: 'One or the "
              f"other must be used consistently.'")


# ===== AC-PACKAGING-21 (ns-segment) =====
def html_cover_urls(html_text: str) -> dict[str, list[str] | None]:
    """Front-matter URL blocks parsed from the rendered HTML cover -- the
    DOCX-native equivalent of stage_urls_from_md(), and the SAME cover
    body-slice/tag-strip/label-cut logic check_html_cover() already runs
    inline (oasis_pub_check.py ~1362-1386), factored out to a single named
    helper so no caller carries its own near-copy of that parser (idiom
    brief: 'Reuse helpers; never copy-paste a walk or a URL parse that
    already exists'). check_html_cover() should be repointed at this helper
    at integration time -- see this check's 'integration_note'.
    Hardened over the inline original in two zero-risk ways (verified not to
    change check_html_cover's own canonical-order-cover fixtures): (1) the
    <body> search and the docs.oasis-open.org URL match are case-insensitive
    (a Word HTML export or converter can emit <BODY> or an uppercase
    scheme/host, and URI scheme+host are case-insensitive by spec); (2) the
    Latest-stage capture additionally stops at a 'Previous (version|stage)'
    label, so a non-canonically-ordered cover (This, Latest, Previous) cannot
    bleed a Previous-stage URL into the Latest-stage result and misclassify
    its severity.
    Returns {'this': ..., 'previous': ..., 'latest': ...}; a value of None
    means the label was not found at all; [] means the label was found but
    no docs.oasis-open.org URL preceded the next label/cut."""
    m_body = re.search(r"<body\b", html_text, re.I)
    cover = html_text[m_body.start() if m_body else 0:][:120000]
    head = re.sub(r"<[^>]+>", " ", cover)
    head = re.sub(r"&nbsp;|&#160;|\s+", " ", head)

    def urls_between(start: str, ends: list[str]) -> list[str] | None:
        m = re.search(start, head, re.I)
        if not m:
            return None
        seg = head[m.end():]
        cut = len(seg)
        for e in ends:
            m2 = re.search(e, seg, re.I)
            if m2:
                cut = min(cut, m2.start())
        return re.findall(r"https?://docs\.oasis-open\.org/[^\s\"<>]+", seg[:cut], re.I)

    return {
        "this": urls_between(r"This (version|stage)",
                              [r"Previous (version|stage)", r"Latest (version|stage)",
                               r"Technical Committee"]),
        "previous": urls_between(r"Previous (version|stage)",
                                  [r"Latest (version|stage)", r"Technical Committee"]),
        "latest": urls_between(r"Latest (version|stage)",
                                [r"Previous (version|stage)", r"Technical Committee",
                                 r"Chairs?\b"]),
    }

def check_ns_segment(md_text: str, html_text: str, f: Findings) -> None:
    """AC-PACKAGING-21: the package's own This/Latest-stage cover URIs may not
    reuse the reserved /ns/ path segment (namespace identifiers only, never a
    retrievable document -- handbook-Naming.txt). Previous-stage hits on the
    same rule are WARN/manual-review: that citation is an immutable historical
    fact the current package cannot alter."""
    if md_text:
        by_role = {
            "This stage": stage_urls_from_md(md_text, "This"),
            "Previous stage": stage_urls_from_md(md_text, "Previous"),
            "Latest stage": stage_urls_from_md(md_text, "Latest"),
        }
    elif html_text:
        # DOCX-native track: no markdown front matter to read, so parse the
        # rendered-cover region via the shared html_cover_urls() helper --
        # the same extraction check_html_cover() uses, no bespoke copy here.
        cover = html_cover_urls(html_text)
        by_role = {
            "This stage": cover["this"] or [],
            "Previous stage": cover["previous"] or [],
            "Latest stage": cover["latest"] or [],
        }
    else:
        by_role = {}

    f.observe("ns-segment",
              cover_uris_scanned=sum(len(v) for v in by_role.values()),
              this_stage_urls=by_role.get("This stage") or "(none)",
              previous_stage_urls=by_role.get("Previous stage") or "(none)",
              latest_stage_urls=by_role.get("Latest stage") or "(none)")

    seen: set[tuple[str, str]] = set()
    for role, urls in by_role.items():
        for u in urls or []:
            clean = u.rstrip(".,)\\")
            segments = [s for s in uri_path(clean).split("/") if s]
            if "ns" not in segments:
                continue
            key = (role, clean)
            if key in seen:
                continue
            seen.add(key)
            if role == "Previous stage":
                f.add(WARN, "ns-segment",
                      f"{clean} is cited as the immediately-preceding-stage document "
                      f"URI and contains the reserved /ns/ segment; this is very likely "
                      f"an inherited historical defect in an already-published, "
                      f"immutable prior stage rather than something the current package "
                      f"can fix -- confirm with Project Administration before treating "
                      f"as blocking.")
            else:
                f.add(BLOCKER, "ns-segment",
                      f"{clean} is declared as the {role} document URI but reuses the "
                      f"reserved /ns/ segment, which handbook-Naming.txt reserves for "
                      f"namespace identifiers, not retrievable documents.")


def run(stage_dir: str, f: Findings) -> None:
    """Output-centric validation. All roads lead to HTML and PDF: whatever the
    authoring format (Markdown, Word, DocBook/XML, LaTeX, ...), the published
    form is HTML + PDF at the canonical URLs, so the bulk of the gate runs on
    those outputs for every package. Source-format checks are add-ons applied
    to whatever source the package carries."""
    version, stage = parse_stage(stage_dir)
    f.observe("stage-name", stage_directory=stage)
    f.observe("version-naming", version_directory=version)
    check_stage_name(stage, f)
    items = find_delivery_items(stage_dir, ("md", "docx", "odt", "html", "pdf"))
    if not items:
        f.add(BLOCKER, "filenames", f"No delivery items found in {stage_dir}")
        return

    md_text = read_text(items["md"]) if "md" in items else ""
    html_text = read_text(items["html"]) if "html" in items else ""
    is_word = "docx" in items and "md" not in items
    is_odt = "odt" in items and "md" not in items and "docx" not in items

    # ---- the bar: HTML + PDF, always; the authoritative source travels ---
    required = ["html", "pdf"]
    if "md" in items:
        required.append("md")        # md-track contract preserves the source
    elif "docx" in items:
        required.append("docx")      # Word-track contract preserves the source
    elif "odt" in items:
        required.append("odt")       # ODT-track contract preserves the source
    stem = check_filenames(items, stage, f, required=tuple(required))
    f.observe("filenames", delivery_files=[os.path.basename(p) for p in items.values()],
              formats_present=sorted(items), required_formats=sorted(required))
    f.observe("version-naming", delivery_stem=stem)
    check_version_naming(version, stem, f)
    if not any(k in items for k in ("md", "docx", "odt")) and "html" in items:
        f.add(WARN, "filenames",
              "No authoritative source artifact (md/docx/odt) in the package root; "
              "DocBook/XML and LaTeX sources should travel with their renderings.")
    if is_word:
        f.add(INFO, "track",
              "Word-authored package (authoritative .docx, no .md): source "
              "add-ons swapped for Word render-fidelity checks.")
    if is_odt:
        f.add(INFO, "track",
              "ODT-authored package (authoritative .odt): the full output and "
              "package suites run, plus the ODT source-integrity checks; the "
              "cover is parsed from the rendered HTML.")
    odt_paths = sorted(
        os.path.join(r, n) for r, _, fs in os.walk(stage_dir) for n in fs
        if n.lower().endswith(".odt"))
    if odt_paths:
        mimetypes = set()
        for op in odt_paths:
            mt = check_odt(op, os.path.relpath(op, stage_dir), f)
            if mt:
                mimetypes.add(mt)
        f.observe("odt-integrity", odt_files=len(odt_paths),
                  mimetypes=", ".join(sorted(mimetypes)) or "(none declared)")

    # ---- output suite: HTML ----------------------------------------------
    base = ""
    if md_text:
        base = check_front_matter(md_text, items, version, stage, f)
    if html_text:
        # anchors are source-side artifacts on Word renders: WARN there
        check_html(html_text, stem, f,
                   anchor_severity=WARN if is_word else BLOCKER)
        if not md_text:
            # no markdown front matter to read: parse the rendered cover,
            # which every publication carries regardless of authoring format
            base = check_html_cover(html_text, version, stage, f)
        if is_word:
            check_generator_meta(html_text, f)
        check_vml_fallback(html_text, f)
        check_asset_refs(stage_dir, items["html"], html_text, f)
        if not md_text:
            prose = re.sub(r"<[^>]+>", " ", strip_code_blocks(html_text, "html"))
            f.observe("dead-lists", html_lists_addresses=sorted(set(
                re.findall(r"[\w.+-]+@lists\.oasis-open\.org", prose))) or "(none)")
            f.observe("case", html_docs_urls_scanned=len(set(
                re.findall(r"https://docs\.oasis-open\.org/\S+", prose))))
            for m in sorted(set(re.findall(r"[\w.+-]+@lists\.oasis-open\.org", prose))):
                f.add(BLOCKER, "dead-lists",
                      f"References mailing address '{m}': lists.oasis-open.org no longer "
                      f"accepts mail (messages fail silently). Point comments at the TC's "
                      f"Higher Logic comment facility instead.")
            for u in set(re.findall(r"https://docs\.oasis-open\.org/\S+", prose)):
                path = u.split("docs.oasis-open.org/", 1)[1].rstrip(".,)\\")
                if path != path.lower() and "/templates/" not in u:
                    f.add(WARN, "case",
                          f"Mixed-case path in docs.oasis-open.org URL (host is "
                          f"case-sensitive): {u}")
    check_revision_collision(base, version, stage, f)
    check_residue(md_text, html_text, f)
    check_member_uri(md_text, html_text, f)
    check_conformance_structure(md_text, html_text, stage_dir, stage, f)
    check_image_policy(stage_dir, html_text, f)
    check_references_split(stage, md_text, html_text, f)
    check_content_labels(md_text, html_text, stage, f)
    check_image_policy(stage_dir, html_text, f)
    check_stage_token(md_text, html_text, stage, f)
    check_image_policy(stage_dir, html_text, f)
    check_title_version(html_text, version, stage, is_word, f)
    check_frontmatter_title_oasis_prefix(html_text, stage, f)
    check_image_policy(stage_dir, html_text, f)
    check_authors(md_text, is_word, is_odt, f)
    check_image_policy(stage_dir, html_text, f)
    check_name_chars(stage_dir, version, stage, stem, f)
    check_extension_count(stage_dir, items, stem, stage, f)
    check_image_policy(stage_dir, html_text, f)
    check_extension_conformance(stage_dir, stage, stem, f)
    check_image_policy(stage_dir, html_text, f)
    check_stable_artifact_names(stage_dir, items, stem, f)
    check_multipart_naming(stage_dir, f)
    check_image_policy(stage_dir, html_text, f)
    check_multipart_part_identifiers(stage_dir, version, stage, f)
    check_image_policy(stage_dir, html_text, f)
    check_public_review_metadata(base, stage, stem, f)
    check_comment_resolution_log(stage_dir, stage, stem, f)
    check_member_uri(md_text, html_text, f)
    check_normdef_refs(stage_dir, items, md_text, html_text, stage, f)
    check_image_policy(stage_dir, html_text, f)
    check_uri_alias(stage_dir, items, md_text, html_text, f)
    check_image_policy(stage_dir, html_text, f)
    check_revision_collision(base, version, stage, f)
    check_residue(md_text, html_text, f)
    check_member_uri(md_text, html_text, f)
    check_xml_namespaces(stage_dir, base, f)
    check_image_policy(stage_dir, html_text, f)
    check_ns_segment(md_text, html_text, f)
    check_image_policy(stage_dir, html_text, f)

    # ---- output suite: PDF -----------------------------------------------
    if "pdf" in items:
        check_pdf(items["pdf"], base, version, f)
        title = _first_h1(md_text)
        if not title and html_text:
            tm = re.search(r"<title>(.*?)</title>", html_text, re.I | re.S)
            title = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""
        check_pdf_cover(items["pdf"], title, f)
        check_pdf_fonts(stage_dir, items["pdf"], html_text, f)

    # ---- source add-ons ---------------------------------------------------
    if md_text:
        check_md_links(md_text, f)
        check_md_fences(md_text, f)
        check_policy(md_text, html_text, version, stage, f)
        check_template(md_text, html_text, f)
        check_correction_classes(md_text, stage_dir, base, stage, f)

    # ---- package suite ----------------------------------------------------
    check_schemas(stage_dir, base, version, stage, f)
    check_hygiene(stage_dir, f, {os.path.basename(p) for p in items.values()})
    check_manifest(stage_dir, f)


def locate_stage_dir(root: str) -> str:
    """Inside an extracted zip, find the deepest dir holding the delivery items."""
    for dirpath, _dirs, files in os.walk(root):
        exts = {os.path.splitext(n)[1].lstrip(".").lower() for n in files}
        if {"md", "html"} <= exts:
            return dirpath
    return root


# ---------------------------------------------------- condition registry
#
# Every individual defect condition the AST advertises (--list-checks) is
# documented here: the condition verified, the value the logic PULLS from the
# package, and what that value is COMPARED TO. Keyed (check, sig) where sig is
# a distinctive literal substring of the condition's finding-message template;
# conditions_inventory() asserts the registry and the AST agree in BOTH
# directions, so an undocumented (or renamed) condition fails the inventory
# instead of silently vanishing from validation reports.
#
# "applies": md = markdown-track packages only, docx = DOCX-native track only,
# both = every package. "requires": a package/environment feature without
# which the condition is not evaluated (reported NA, never a fake PASS).
# "sites": number of identical f.add call sites this entry covers (default 1).

CONDITION_DOCS: list[dict] = [
    # stage-name
    dict(check="stage-name", sig="is missing its two-digit number", applies="both",
         condition="Stage directory name carries a two-digit revision number",
         pulls="the stage directory name",
         compares_to="valid stage prefixes must carry a two-digit suffix (csd01, never bare csd)"),
    dict(check="stage-name", sig="uses a retired/invalid stage token", applies="both",
         condition="Stage token is not a retired abbreviation",
         pulls="the alphabetic prefix of the stage directory name",
         compares_to="retired token set (csprd, cnprd, cos, csdpr, cndpr) per Naming Directives v1.7"),
    dict(check="stage-name", sig="is not a recognized stage token", applies="both",
         condition="Stage token is a recognized current stage",
         pulls="the alphabetic prefix of the stage directory name",
         compares_to="valid stage set: wd, csd, cs, cnd, cn, os, ps, psd, pn, pnd, errata"),
    # version-naming
    dict(check="version-naming", sig="does not match the vN.N convention", applies="both",
         condition="Version directory matches the vN.N(.N) convention",
         pulls="the version directory name from the package path",
         compares_to="the Naming Directives version-segment pattern vN.N(.N), e.g. v1.0, v2.0.1"),
    dict(check="version-naming", sig="the files were renamed", applies="both",
         condition="Version embedded in the delivery filename agrees with the version directory",
         pulls="the version segment embedded in the delivery filename stem",
         compares_to="the version directory the package publishes under"),
    dict(check="version-naming", sig="does not embed the version segment", applies="both",
         condition="Delivery filename embeds the version segment",
         pulls="the delivery filename stem",
         compares_to="the Naming Directives filename shape <base>-<version>-<stage>"),
    # revision-collision
    dict(check="revision-collision", sig="is already published at", applies="both", requires="network",
         condition="The submitted stage does not already exist on the live site",
         pulls="the HTTP status of the this-stage URL on docs.oasis-open.org",
         compares_to="expected non-200 for a NEW submission; an existing stage means the revision must increment"),
    # filenames
    dict(check="filenames", sig="No delivery items found", applies="both",
         condition="The stage directory contains delivery items at all",
         pulls="the file listing of the stage directory root",
         compares_to="at least one delivery item (md/docx/odt/html/pdf) must be present"),
    dict(check="filenames", sig="do not share one basename", applies="both",
         condition="All delivery items share one basename",
         pulls="the set of delivery-item filename stems",
         compares_to="exactly one distinct stem across md/docx/odt/html/pdf"),
    dict(check="filenames", sig="carries a working token", applies="both",
         condition="Delivery filename carries no working token",
         pulls="the delivery filename stem",
         compares_to="forbidden working tokens: draft, tmp, rc (files are named for the published stage)"),
    dict(check="filenames", sig="does not end in '-", applies="both",
         condition="Delivery filename ends in the stage suffix",
         pulls="the delivery filename stem",
         compares_to="the stage directory name as a -<stage> suffix"),
    dict(check="filenames", sig="Missing delivery format(s)", applies="both",
         condition="All required delivery formats are present",
         pulls="the set of delivery formats found in the package",
         compares_to="the track's required set: html+pdf plus the authoritative source (md, docx, or odt)"),
    dict(check="filenames", sig="No authoritative source artifact", applies="both",
         condition="An authoritative source artifact travels with the renderings",
         pulls="the set of source formats found in the package root",
         compares_to="at least one authoritative source (.md, .docx, or .odt) expected beside HTML/PDF"),
    # front-matter (markdown track: 1-9; DOCX track cover: 10-12)
    dict(check="front-matter", sig="No 'This stage' URL block", applies="md",
         condition="Markdown front matter carries a This-stage URL block",
         pulls="URLs under the 'This Stage/Version' heading in the markdown",
         compares_to="at least one URL must be declared"),
    dict(check="front-matter", sig="Stage URL is not under", applies="md",
         condition="Every stage URL is under docs.oasis-open.org",
         pulls="each URL in the This/Latest stage blocks",
         compares_to="the canonical site prefix https://docs.oasis-open.org/"),
    dict(check="front-matter", sig="This-stage URL does not contain", applies="md",
         condition="This-stage URLs carry the version and stage path segments",
         pulls="each URL in the This-stage block",
         compares_to="the package's /<version>/ and /<stage>/ path segments"),
    dict(check="front-matter", sig="which is not a file in the package", applies="md",
         condition="Every This-stage URL points at a file included in the package",
         pulls="the filename each This-stage URL points at",
         compares_to="the set of delivery filenames actually in the package"),
    dict(check="front-matter", sig="This-stage block does not list", applies="md",
         condition="The This-stage block lists all three artifacts (md, html, pdf)",
         pulls="the artifact extensions listed in the This-stage block",
         compares_to="the full delivery set: .md, .html, .pdf"),
    dict(check="front-matter", sig="Latest-stage URL must point at the version root", applies="md",
         condition="Latest-stage URLs point at the persistent version root",
         pulls="each URL in the Latest-stage block",
         compares_to="must NOT contain the /<stage>/ segment (latest is the version-root path)"),
    dict(check="front-matter", sig="Latest-stage URL not under", applies="md",
         condition="Latest-stage URLs are under the package's version directory",
         pulls="each URL in the Latest-stage block",
         compares_to="the package's /<version>/ path segment"),
    dict(check="front-matter", sig="confirm this is an intentional external reference", applies="md",
         condition="Any docs.oasis-open.org URL declaring a different version is intentional",
         pulls="every docs.oasis-open.org URL in the markdown outside Previous/Related-work blocks",
         compares_to="the package's own version; a different version is a stale-draft tell unless external"),
    dict(check="front-matter", sig="'Latest'-labelled URL carries the stage segment", applies="md",
         condition="No Latest-labelled line cites a stage-pinned URL for this spec",
         pulls="URLs on lines labelled 'Latest' in the prose",
         compares_to="the persistent version-root form (no /<stage>/ segment)"),
    # uri-chars  (AC-NAMING-08; Naming Directives v1.7 s3)
    dict(check="uri-chars", sig="Underscore in a document (cover-page) URI", applies="md",
         condition="No underscore appears in a This/Latest-stage document URI",
         pulls="the percent-decoded path of each This-stage and Latest-stage cover URI",
         compares_to="Naming Directives v1.7 s3: '_' is barred from any filename or "
                     "directory name used in a document URI"),
    # member-uri  (AC-PACKAGING-18; Naming Directives v1.7 s6.6)
    dict(check="member-uri", sig="Cites an OASIS member-only (Kavi) URI", applies="both",
         condition="No OASIS member-only (Kavi) URI is cited in the package",
         pulls="every oasis-open.org /apps/org/ or /committees/download.php URL in the md and html",
         compares_to="Naming Directives v1.7 s6.6: member-only (password-protected) Kavi "
                     "references must not appear in public TC documents"),
    dict(check="front-matter", sig="No 'This version' URL block found on the HTML cover", applies="docx",
         condition="HTML cover carries a This-version URL block",
         pulls="URLs following 'This version/stage' on the rendered HTML cover",
         compares_to="at least one URL must be present"),
    dict(check="front-matter", sig="This-version URL does not contain", applies="docx",
         condition="Cover This-version URLs carry the version and stage segments",
         pulls="each URL in the cover's This-version block",
         compares_to="the package's /<version>/ and /<stage>/ path segments"),
    dict(check="front-matter", sig="Latest-version URL must point at the version root", applies="docx",
         condition="Cover Latest-version URLs point at the persistent version root",
         pulls="each URL in the cover's Latest-version block",
         compares_to="must NOT contain the /<stage>/ segment"),
    # residue
    dict(check="residue", sig="Editor TODO left in", applies="both",
         condition="No editor TODO markers left in prose",
         pulls="prose of the markdown and HTML (code blocks stripped)",
         compares_to="the patterns TODO(...) and TODO: must not occur"),
    dict(check="residue", sig="'tbd' placeholder section", applies="both",
         condition="No bare 'tbd' placeholder sections",
         pulls="prose of the markdown and HTML (code blocks stripped)",
         compares_to="no line consisting solely of 'tbd'"),
    dict(check="residue", sig="Template instruction left in", applies="both",
         condition="No template editor-instruction text left in the published prose",
         pulls="prose of the markdown and HTML (code blocks stripped)",
         compares_to="the OASIS Board-approved work product templates, which state that "
                     "'All template instructions ... need to be deleted prior to publication'; "
                     "an imperative to remove/delete something 'before publication' or 'prior to "
                     "publication' surviving in the prose means an instruction block reached publication"),
    dict(check="residue", sig="'Will be filled in", applies="both",
         condition="No 'Will be filled in' placeholders (early-stage tolerated, must resolve before CS)",
         pulls="prose of the markdown and HTML (code blocks stripped)",
         compares_to="the phrase 'Will be filled in' must not occur"),
    # html-title
    dict(check="html-title", sig="carries working residue", applies="both",
         condition="HTML title carries no working residue",
         pulls="the <title> element text",
         compares_to="must not end in tmp, draft, or wip"),
    dict(check="html-title", sig="looks too short", applies="both",
         condition="HTML title is a plausible document title",
         pulls="the <title> element text and its length",
         compares_to="a full spec title (at least 8 characters)"),
    # html-residue
    dict(check="html-residue", sig="title-block-header", applies="both",
         condition="No stale pandoc title-block header in the HTML",
         pulls="the HTML body",
         compares_to="the <header id=\"title-block-header\"> element must be absent (lint D2)"),
    dict(check="html-residue", sig="CI runner path leaked into the HTML", applies="both",
         condition="No CI runner paths in HTML hrefs or srcs",
         pulls="every href/src attribute in the HTML",
         compares_to="the /home/runner/ path prefix must not occur (lint D3)"),
    dict(check="html-residue", sig="<h1> elements", applies="both",
         condition="The document title appears in exactly one H1",
         pulls="the count of <h1> elements matching the title text",
         compares_to="exactly 1 (more renders the title twice on the PDF cover, lint D1)"),
    # html-anchors
    dict(check="html-anchors", sig="has no matching anchor in the HTML", applies="both",
         severity="BLOCKER/WARN",  # dynamic: BLOCKER on the md track, WARN on DOCX-native (source-DOCX artifact)
         condition="Every internal fragment link resolves to an anchor",
         pulls="each internal href (#...) and the set of element ids/anchor names",
         compares_to="every referenced fragment must exist as an id or <a name>"),
    dict(check="html-anchors", sig="no internal (fragment) links at all", applies="both",
         condition="The HTML carries a linked table of contents",
         pulls="the count of internal fragment links",
         compares_to="at least one expected (a spec HTML without any is missing its TOC links)"),
    # md-links
    dict(check="md-links", sig="Dual link", applies="md",
         condition="No dual [url](url) links in the markdown",
         pulls="every [text](target) link where text is itself a URL",
         compares_to="text and target being the same URL calls for a bare autolink or real anchor text"),
    dict(check="md-links", sig="pandoc autolink pulls the", applies="md",
         condition="No bare URL runs into '.\\' without a space",
         pulls="each markdown line ending a URL with .\\",
         compares_to="the safe form '. \\' (otherwise pandoc pulls the period and backslash into the href)"),
    # fence-collapse
    dict(check="fence-collapse", sig="collapses to inline code", applies="md",
         condition="No opening code fence carries trailing text in its info string",
         pulls="each opening fence line's info string",
         compares_to="a bare language token or curly-attribute form; trailing text collapses the block (lint D6)"),
    # image-policy
    dict(check="image-policy", sig="Empty <img src>", applies="both",
         condition="No empty img src attributes",
         pulls="each <img> tag's src attribute",
         compares_to="src must be non-empty"),
    dict(check="image-policy", sig="Absolute-path <img src=", applies="both",
         condition="No absolute-path image sources",
         pulls="each <img> tag's src attribute",
         compares_to="a leading / resolves outside the package on publication"),
    dict(check="image-policy", sig="Path-traversal <img src=", applies="both",
         condition="No path-traversal image sources",
         pulls="each <img> tag's src attribute",
         compares_to="the path must not contain .. segments"),
    dict(check="image-policy", sig="<img srcset> present", applies="both",
         condition="No responsive srcset image constructs",
         pulls="each <img> tag's attributes",
         compares_to="the publication pipeline's self-containment policy refuses srcset"),
    dict(check="image-policy", sig="<picture> element present", applies="both",
         condition="No <picture> elements",
         pulls="the HTML body",
         compares_to="the publication pipeline's self-containment policy refuses <picture>"),
    dict(check="image-policy", sig="per-image refusal cap", applies="both",
         condition="Every image file is under the per-image size cap",
         pulls="the byte size of each image file in the package",
         compares_to="the pipeline's 2MB per-image refusal cap"),
    dict(check="image-policy", sig="SVG contains <script>", applies="both",
         condition="No SVG carries script content",
         pulls="the body of each .svg file",
         compares_to="<script> elements are active content, refused on docs.oasis-open.org"),
    dict(check="image-policy", sig="inline event handlers", applies="both",
         condition="No SVG carries inline event handlers",
         pulls="the body of each .svg file",
         compares_to="on*= attributes are active content, refused"),
    dict(check="image-policy", sig="references an external image/use target", applies="both",
         condition="No SVG references external image or use targets",
         pulls="the body of each .svg file",
         compares_to="external <image>/<use> hrefs break self-containment"),
    dict(check="image-policy", sig="Cumulative image payload", applies="both",
         condition="Total image payload is under the cumulative cap",
         pulls="the summed byte size of all image files",
         compares_to="the pipeline's 5MB cumulative inlining cap"),
    # pdf-cover
    dict(check="pdf-cover", sig="times on the PDF cover page", applies="both", requires="pdftotext",
         condition="The document title appears exactly once on the PDF cover page",
         pulls="the count of title occurrences in the PDF's first page text",
         compares_to="exactly 1 (more means stale title-block residue baked into the render, assertion A1)"),
    dict(check="pdf-cover", sig="leaked into the rendered PDF text", applies="both", requires="pdftotext",
         condition="No CI runner path anywhere in the PDF text",
         pulls="the full extracted PDF text",
         compares_to="the /home/runner/ path must not occur (assertion A2)"),
    # schema-id
    dict(check="schema-id", sig="not valid JSON (", applies="both", requires="schemas",
         condition="Every .json file in the package parses as JSON",
         pulls="each .json file's content",
         compares_to="must parse without error"),
    dict(check="schema-id", sig="a flattened path under the version", applies="both", requires="schemas",
         condition="A flattened $id under the version root is a conscious convention",
         pulls="each schema's declared $id",
         compares_to="the file's publish path; a version-root flattened $id (CSAF v2.0 style) needs a copy at that location"),
    dict(check="schema-id", sig="An implementer following the $id", applies="both", requires="schemas",
         condition="Each schema's $id agrees with where the file publishes",
         pulls="each schema's declared $id",
         compares_to="the canonical latest-version URL derived from the package path"),
    dict(check="schema-id", sig="disagrees with $id", applies="both", requires="schemas",
         condition="Schema-internal self-references agree with the declared $id",
         pulls="every docs.oasis-open.org .json URL inside each schema body",
         compares_to="the schema's own declared $id"),
    # pdf-sync
    dict(check="pdf-sync", sig="pdftotext not on PATH", applies="both",
         condition="The PDF cross-check toolchain is available",
         pulls="the PATH lookup for pdftotext (poppler)",
         compares_to="pdftotext present; absent means the PDF front-matter cross-check is skipped here and runs at intake"),
    dict(check="pdf-sync", sig="pdftotext failed", applies="both", requires="pdftotext",
         condition="pdftotext executes against the PDF",
         pulls="the pdftotext process outcome",
         compares_to="a clean execution"),
    dict(check="pdf-sync", sig="pdftotext could not read the PDF", applies="both", requires="pdftotext",
         condition="The PDF is machine-readable",
         pulls="pdftotext's exit status on the delivery PDF",
         compares_to="exit 0"),
    dict(check="pdf-sync", sig="does not contain the canonical this-stage base URL", applies="both", requires="pdftotext",
         condition="The PDF front matter carries the canonical this-stage URL",
         pulls="the first three pages of extracted PDF text",
         compares_to="the this-stage base URL declared by the package front matter"),
    dict(check="pdf-sync", sig="expected only as a previous-stage reference", applies="both", requires="pdftotext",
         condition="The PDF cites no unexpected other version of this spec",
         pulls="every this-spec version URL in the extracted PDF text",
         compares_to="the package's own version (previous-stage citations expected, anything else confirmed)"),
    # template
    dict(check="template", sig="Required front-matter section missing", applies="md",
         condition="All required template front-matter sections are present",
         pulls="the markdown headings",
         compares_to="the template's required set: This/Previous/Latest stage, Technical Committee, Chairs, Editors, Abstract"),
    dict(check="template", sig="out of template order", applies="md",
         condition="Front-matter sections appear in template order",
         pulls="the order of found front-matter sections",
         compares_to="the canonical template ordering"),
    dict(check="template", sig="No Conformance section found", applies="md",
         condition="A Conformance section exists",
         pulls="the markdown headings",
         compares_to="the TC Process requirement: every Standards Track Work Product carries conformance clauses"),
    # template-css
    dict(check="template-css", sig="the template look is Liberation", applies="md",
         condition="A non-canonical stylesheet keeps the template font family",
         pulls="the primary font-family declared by the HTML's own stylesheet",
         compares_to="the template look: Liberation Sans / Arial / Helvetica"),
    dict(check="template-css", sig="no stylesheet at all", applies="md",
         condition="The HTML carries a stylesheet",
         pulls="the HTML's <link rel=stylesheet> and <style> elements",
         compares_to="at least one styling source must be present"),
    # package-refs
    dict(check="package-refs", sig="is not in the package: it will 404", applies="md",
         condition="Every file the document cites under its own stage path is included in the package",
         pulls="each cited URL under the this-stage base and the package file tree",
         compares_to="the cited relative path must exist as a file in the package"),
    # link-mismatch
    dict(check="link-mismatch", sig="Visible URL and link target disagree", applies="md",
         condition="Visible URL text and its link target agree",
         pulls="each [shown-url](target-url) pair in the prose",
         compares_to="shown and target must be the same URL (a disagreement is a rename artifact)"),
    # double-slash
    dict(check="double-slash", sig="contains a double slash", applies="md",
         condition="No relative link path contains a double slash",
         pulls="each relative link target in the prose",
         compares_to="single slashes only (the CDN 404s a double slash even where browsers tolerate it)"),
    # cover-hr
    dict(check="cover-hr", sig="Horizontal rule between the OASIS logo", applies="md",
         condition="No horizontal rule between the OASIS logo and the title",
         pulls="the first 600 characters of the markdown",
         compares_to="no --- / *** / ___ rule after the logo (the publication CSS renders it as a PDF page break)"),
    # pdf-fonts
    dict(check="pdf-fonts", sig="pdffonts failed", applies="both", requires="pdffonts",
         condition="pdffonts executes against the PDF",
         pulls="the pdffonts process outcome",
         compares_to="a clean execution"),
    dict(check="pdf-fonts", sig="not declared by the package's own CSS", applies="both", requires="pdffonts",
         condition="The PDF's embedded fonts are declared by the package's own CSS",
         pulls="the font base names embedded in the PDF (pdffonts)",
         compares_to="the font families declared in the package's HTML/CSS (its own typography authority)"),
    # manifest
    dict(check="manifest", sig="manifest.json is not valid JSON", applies="both", requires="manifest",
         condition="manifest.json parses as JSON",
         pulls="the manifest.json content",
         compares_to="must parse without error"),
    dict(check="manifest", sig="manifest lists missing file", applies="both", requires="manifest",
         condition="Every manifest item exists in the package",
         pulls="each path listed in the manifest",
         compares_to="the package file tree"),
    dict(check="manifest", sig="sha256 mismatch for", applies="both", requires="manifest",
         condition="Every manifest sha256 matches the file's actual digest",
         pulls="the sha256 of each manifest-listed file",
         compares_to="the digest recorded in the manifest"),
    # junk-files
    dict(check="junk-files", sig="Working directory", applies="both",
         condition="No working directories inside the package",
         pulls="every directory name in the package tree",
         compares_to="forbidden set: __MACOSX, .git, .venv, venv, node_modules"),
    dict(check="junk-files", sig="Junk file in package", applies="both",
         condition="No OS junk or editor backup files in the package",
         pulls="every filename in the package tree",
         compares_to="forbidden: .DS_Store, Thumbs.db, desktop.ini, and ~ / .bak / .orig / .swp suffixes"),
    # case
    dict(check="case", sig="Mixed-case filename", applies="both",
         severity="BLOCKER/WARN",  # dynamic at the call site: delivery files block, auxiliary files warn
         condition="Every filename in the package is lowercase",
         pulls="every filename in the package tree",
         compares_to="its lowercase form (the publication origin is case-sensitive; the canonical logo filename is exempt)"),
    dict(check="case", sig="Mixed-case path in docs.oasis-open.org URL", applies="both", sites=2,
         condition="Every self-referential docs.oasis-open.org URL path is lowercase",
         pulls="every docs.oasis-open.org URL in the prose (markdown source on the md track, rendered HTML on the DOCX track)",
         compares_to="its lowercase form (case-sensitive origin; /templates/ paths exempt)"),
    # odt-integrity
    dict(check="odt-integrity", sig="does not open as a ZIP archive", applies="odt",
         condition="The ODT source opens as a ZIP archive",
         pulls="the result of opening the .odt with the stdlib zip reader",
         compares_to="a readable OpenDocument container"),
    dict(check="odt-integrity", sig="has no mimetype member", applies="odt",
         condition="The ODT archive carries a mimetype member",
         pulls="the archive member listing",
         compares_to="the OpenDocument package requirement of a mimetype entry"),
    dict(check="odt-integrity", sig="which is not an OpenDocument type", applies="odt",
         condition="The declared mimetype is an OpenDocument type",
         pulls="the content of the mimetype member",
         compares_to="the application/vnd.oasis.opendocument.* family"),
    dict(check="odt-integrity", sig="has no content.xml", applies="odt",
         condition="The ODT archive carries the document body (content.xml)",
         pulls="the archive member listing",
         compares_to="the OpenDocument package requirement of a content.xml body"),
    dict(check="odt-integrity", sig="does not parse as XML", applies="odt",
         condition="The ODT document body parses as XML",
         pulls="content.xml, parsed with the stdlib XML parser",
         compares_to="well-formed XML"),
    dict(check="odt-integrity", sig="carries embedded macro/script content", applies="odt",
         condition="The ODT carries no embedded macros or scripts",
         pulls="archive member paths under Basic/ and Scripts/",
         compares_to="the host's active-content policy (none permitted, same as SVG scripts)"),
    # symlinks
    dict(check="symlinks", sig="points at its own ancestor", applies="both",
         condition="No symlink points at itself or an ancestor directory",
         pulls="each symlink's resolved target",
         compares_to="must not equal or contain its own directory (deploys materialize symlinks into unbounded recursion)"),
    # dead-lists
    dict(check="dead-lists", sig="References mailing address", applies="both", sites=2,
         condition="No reference to a lists.oasis-open.org mailing address",
         pulls="every @lists.oasis-open.org address in the prose (markdown source on the md track, rendered HTML on the DOCX track)",
         compares_to="the dead-infrastructure rule: that mail host silently fails; comments route via Higher Logic"),
    dict(check="dead-lists", sig="archives", applies="md",
         condition="Links into the retired list archives are flagged for verification",
         pulls="lists.oasis-open.org/archives links in the prose",
         compares_to="each must be individually verified while the archive infrastructure is retired"),
    # rfc-keywords
    dict(check="rfc-keywords", sig="does not cite RFC 2119", applies="md",
         condition="Normative key words are backed by an RFC 2119 citation",
         pulls="normative key words (MUST, SHALL, SHOULD, MAY, ...) found in the prose",
         compares_to="an RFC 2119 citation must be present when key words are used"),
    dict(check="rfc-keywords", sig="RFC 8174", applies="md",
         condition="RFC 2119 citation is paired with RFC 8174",
         pulls="the RFC citations in the document",
         compares_to="the current template cites both 2119 and 8174 (uppercase-only clarification)"),
    # logo
    dict(check="logo", sig="is not the canonical", applies="md",
         condition="The cover logo is the canonical OASIS logo",
         pulls="each logo image source in the markdown",
         compares_to="https://docs.oasis-open.org/templates/OASISLogo-v3.0.png"),
    # previous-stage
    dict(check="previous-stage", sig="the Previous-Stage block is empty or N/A", applies="md",
         condition="A stage past 01 cites its previous stage",
         pulls="the URLs in the markdown's Previous-stage block",
         compares_to="at least one docs.oasis-open.org URL required when the revision number exceeds 01"),
    dict(check="previous-stage", sig="no Previous-version block with docs.oasis-open.org URLs found on the HTML cover", applies="docx",
         condition="A stage past 01 cites its previous stage on the HTML cover",
         pulls="the URLs in the cover's Previous-version block",
         compares_to="at least one docs.oasis-open.org URL required when the revision number exceeds 01"),
    # date-sync
    dict(check="date-sync", sig="the HTML was rendered from a different revision", applies="md",
         condition="The markdown front-matter date appears in the HTML",
         pulls="the document date heading from the markdown",
         compares_to="the rendered HTML text (absence means the HTML came from a different revision)"),
    dict(check="date-sync", sig="Copyright year", applies="md",
         condition="The copyright year matches the document date year",
         pulls="the year in the OASIS copyright line",
         compares_to="the year of the front-matter document date"),
    # generator (DOCX track)
    dict(check="generator", sig="must be produced by Microsoft Word", applies="docx",
         condition="A DOCX-native render was produced by Microsoft Word",
         pulls="the HTML Generator meta content",
         compares_to="must contain 'Microsoft Word' (a LibreOffice render differs in kind from the TC's precedent)"),
    # vml-fallback
    dict(check="vml-fallback", sig="browsers that ignore VML show nothing", applies="both",
         condition="Every VML image has an <![if !vml]> img fallback",
         pulls="the counts of v:imagedata elements and vml-fallback img tags",
         compares_to="fallback count must cover VML count (the invisible-cover-logo class)"),
    # asset-refs
    dict(check="asset-refs", sig="which is not in the package; it 404s", applies="both",
         condition="Every relative src/href the HTML references is included in the package",
         pulls="each package-relative src/href in the HTML (attribute values flattened across Word line wraps)",
         compares_to="the package file tree; a missing target 404s on publication"),
    dict(check='conformance-structure', sig='Conformance section is a buried subsection', applies='both', condition="At least one Conformance heading is a genuine top-level numbered section (not nested deeper than the document's modal top-level depth, and not under an Annex/Appendix ancestor)", pulls="every heading's nesting level, leading number prefix, and Annex/Appendix ancestor chain (markdown ATX headings, or rendered HTML h1-h6 on the DOCX-native track), with code-block content stripped first", compares_to="handbook-Conformance.txt: 'a separate, top-level numbered section of the work product (not a subsection buried elsewhere)'; BLOCKER at cs/os (WARN at wd/csd, or when the modal-depth signal itself is low-confidence)", severity='BLOCKER/WARN'),
    dict(check='conformance-structure', sig='not populated with numbered clauses', applies='both', condition='Each conformance profile scope yields at least one extracted clause identifier', pulls="numbered sub-headings and paragraph-leading 'Clause N'/bracketed target-id labels within the Conformance section span, scoped per named profile", compares_to="handbook-WPQualityRequirements.txt: 'a set of numbered conformance clauses to which any implementation must adhere'; BLOCKER at cs/os, WARN at wd/csd (fail-closed either way, so an empty section is reported rather than passing silently)"),
    dict(check='conformance-structure', sig='Duplicate clause number', applies='both', condition='No clause identifier repeats within the same profile scope', pulls="the extracted clause-identifier set, scoped per named conformance profile (Core/Extended-style sub-headings matching 'Profile'/'Level')", compares_to="handbook-Conformance.txt: 'individually numbered conformance clauses ... so that implementers and Statements of Use can cite specific clauses by number'; BLOCKER at cs/os, WARN at wd/csd", severity='BLOCKER/WARN'),
    dict(check='conformance-structure', sig='Clause number removed/renumbered', applies='both', condition='Every (profile, clause number) pair in the previous stage is still present in this stage (append-only extension is fine; removal/renumbering, including a whole profile silently disappearing, is flagged)', pulls="the ((profile, clause number) -> content hash) map extracted from the resolvable previous-stage artifact, diffed against this stage's map", compares_to="handbook-WPQualityRequirements.txt 'Key principles': 'Clause numbering must be unique and stable across revisions'. Guidelines-sourced (recommended, not mandatory) so WARN-tier informational, never BLOCKER, and never fired for the CS->OS transition (that gets the zero-tolerance override instead)"),
    dict(check='conformance-structure', sig='Clause silently renumbered', applies='both', condition='A (profile, clause number) pair missing from this stage does not reappear under a DIFFERENT number in the same profile with the same content (a disguised renumber-via-delete-and-re-add)', pulls='content-hash collisions between a previous-stage clause and any current-stage clause, scoped within the same profile', compares_to="the same Guidelines stability principle as 'removed/renumbered'; WARN-tier informational"),
    dict(check='conformance-structure', sig='OS conformance clause numbering differs from approved CS', applies='both', condition='At the CS->OS transition, the current (profile, clause id) key set is a byte-for-byte match to the approved-CS key set, scoped per profile, so a whole profile silently dropped while a surviving profile happens to reuse its bare clause numbers is still caught', pulls="the (profile, clause-identifier) sets extracted from the OS package and from the artifact named by its Previous-stage URI (verified to be the approved CS by stage token), each parsed with the extractor matching that artifact's own format (markdown or rendered HTML)", compares_to="handbook-Conformance.txt 'OASIS Standard os': 'Conformance clauses are preserved unchanged from the approved Committee Specification' (TC Process 2.9): zero tolerance, always BLOCKER"),
    dict(check='conformance-structure', sig='OS conformance clause wording differs from approved CS under a stable number', applies='both', condition='A clause whose (profile, number) key is unchanged at CS->OS is flagged for manual confirmation when its content hash changed', pulls='content-hash comparison, per (profile, clause number) key, between the approved CS and the OS package, restricted to keys present in both sets', compares_to="handbook-WPQualityRequirements.txt 'Allowed changes during publication': coordinated non-material changes are permitted (TC Process 2.2.4); not itself a zero-tolerance failure, so WARN/manual-review, never an automatic BLOCKER"),
    dict(check='conformance-structure', sig='Cannot verify CS-preservation requirement', applies='both', condition='At the CS->OS transition, the approved-CS baseline artifact must be resolvable to verify clause-set preservation at all', pulls='the resolution outcome (local sibling stage directory, then network fetch) of the Previous-stage URI naming the approved CS', compares_to="TC Process 2.9's preservation obligation cannot be verified for a Standards Track OS approval if the CS baseline is unreachable, so it is elevated to BLOCKER rather than reported as a silent WARN"),
    dict(check='conformance-structure', sig='Stability not verified - previous stage unavailable', applies='both', condition='A general (non-CS->OS) stability diff that could not resolve its previous-stage artifact is visible in the report, not silently skipped', pulls='the resolution outcome of the Previous-stage URI', compares_to='the general stability check is WARN-tier informational; an unresolvable prior artifact (first publication is a separate, silent no-op) still surfaces the gap as a WARN'),
    dict(check='references-split', sig='is not labeled Normative References / Informative References', applies='both', condition="A bare 'References' heading carrying 2+ direct reference entries is split into separately labeled Normative/Informative child headings (or is too small a sample, 0 or 1 entries, to judge)", pulls="H1-H3 headings normalizing to 'references' plus the distinct reference-entry IDs found directly in that heading's own span (before its first immediate-child heading)", compares_to="handbook-WPQualityChecklist.txt editorial quality checklist bullet: 'normative references listed separately from informative references' (WARN: staff-maintained best-practice checklist, not a TC Process must/shall clause)"),
    dict(check='references-split', sig='is listed under both Normative References and', applies='both', condition='No reference-entry ID appears under both a Normative References heading and an Informative References heading anywhere in the document', pulls="the set of reference-entry IDs found in the span of every 'normative references'-classified heading, and the same for every 'informative references'-classified heading", compares_to='the two ID sets must not intersect; a shared ID is a labeling inconsistency or editorial duplication (handbook-WPQualityChecklist.txt same checklist bullet)'),
    dict(check='content-labels', sig='the Handbook classifies Examples as non-normative content', applies='both', condition='Every Examples/Illustrative-Examples/Sample-<noun> heading carries a structural content-type label (heading suffix, first-sentence lead/predicate, labeled ancestor heading, or document-wide blanket statement)', pulls='markdown ATX/setext headings (or, DOCX-native track, rendered HTML h1-h6 elements via an HTMLParser walk, entities decoded), in document order, each with its heading text, nesting level, and the first sentence of the body block immediately following it', compares_to="handbook-Conformance.txt 'Normative versus non-normative content': Examples content is classified non-normative and 'should be clearly labelled'"),
    dict(check='stage-token', sig='carries a retired stage token', applies='both', condition='Previous-stage URL stage token is not a retired abbreviation', pulls="the stage-abbreviation token extracted from the Previous-stage URL's directory segment and/or filename stem", compares_to='retired token set (csprd, cnprd, cos, csdpr, cndpr) per Naming Directives v1.7; WARN with a legacy-URI verification caveat since a pre-2024 Previous-stage URI may permanently retain a retired token (naming-directives.txt 6.3 Resource Permanence)'),
    dict(check='stage-token', sig="carries stage token '", applies='both', condition="Previous-stage URL stage token matches the document's own current csd/cnd stage abbreviation", pulls="the stage-abbreviation token extracted from the Previous-stage URL's directory segment and/or filename stem", compares_to="the document's own current stage token (handbook-PublicReviews.txt: the cover page URIs 'should all reflect the csd stage abbreviation')"),
    dict(check='stage-token', sig='embeds a stage-abbreviation token', applies='both', condition="Latest-stage URL's filename embeds no stage-abbreviation/revision token at all", pulls='the filename-stem-position stage-abbreviation token (if any) extracted from the Latest-stage URL', compares_to="naming-directives.txt 6.2: the Latest-stage locator URI 'does not contain the path component [stage-abbrev][revisionNumber] or stage identifier in the filename', an absolute prohibition independent of whether the token matches the current stage"),
    dict(check='title-version', sig='does not incorporate a Version identifier', applies='both', condition="The rendered cover-page title incorporates the package's own Version identifier", pulls='the resolved cover-page title text (HTML <title>/<h1> on the markdown track, the MsoTitle-styled or first non-empty non-logo cover paragraph on the DOCX-native track)', compares_to="naming-directives.txt 5.1: 'A Version identifier must also be incorporated into a Work Product name/title'"),
    dict(check='title-version', sig="cites a different Version than the package's own Version identifier", applies='both', condition="The Version cited in the title agrees with the package's own Version identifier", pulls="the numeric run of the rightmost 'Version <n>' token in the resolved title", compares_to="the package's own Version identifier (the version directory segment, with a leading 'v' stripped per naming-directives.txt Section 4's [version-id] grammar)"),
    dict(check='title-version', sig='Version composition does not follow the required', applies='both', condition="The title's Version token is composed as '<name/identifier> Version <number>' with no forbidden punctuation before it and only a sanctioned continuation after it", pulls="the characters immediately preceding and following the rightmost 'Version <n>' token in the resolved title, and the stage token's track classification", compares_to="naming-directives.txt Section 7: MUST for Standards Track (csd/cs/os/errata) -> BLOCKER; SHOULD for Non-Standards Track (cnd/cn) -> WARN with the 'reasonable grounds for alternate constructions' exception; WARN also for any stage token outside the six Section-5.2-enumerated tokens (track unresolved, no corpus citation, never escalated to BLOCKER on an uncited classification)", severity='BLOCKER/WARN'),
    dict(check='title-oasis-prefix', sig="Work Product title begins with 'OASIS'", applies='both', condition="The Work Product title (the <h1> identified by _h1_title_match_info's 'exact' or 'singular-related-fallback' classification) does not begin with the word 'OASIS'", pulls="the <h1> text identified by _h1_title_match_info: either the single <h1> exactly matching the rendered <title> text (the same match check_html's own D1 lint uses for its duplicate-title finding), or, when no exact match exists, the document's sole <h1> when it shares a prefix relationship with <title> (e.g. a trailing brand suffix on <title> alone), flagged lower-confidence in that case", compares_to='naming-directives.txt s7: \'Preferably, a title should not begin with the name "OASIS" except on the recommendation of Project Administration for special cases.\' Section 7\'s lead sentence track-scopes this to BLOCKER (Standards Track, must-observe) / WARN (Non-Standards Track, should-follow with an additional alternate-construction escape valve).', severity='BLOCKER/WARN'),
    dict(check='authors', sig='No Authors section or byline found', applies='md', condition='A Technical Report/Technical Report Draft names its Authors on the cover page (heading or title-block byline)', pulls="a '## Authors'/'## Author(s)' heading (scoped to the front-matter window through Abstract), or a 'by <Name>' title-block byline (scoped to the title/type-label window), on a package whose cover-adjacent type label is Technical Report or Technical Report Draft", compares_to="TC Handbook, Technical Reports: 'A Technical Report has one or more named Authors ... recorded on the cover page'"),
    dict(check='authors', sig='Authors section is empty or placeholder-only', applies='md', condition='The Authors heading/byline is not empty or placeholder-only (tbd/n/a/none), including list/task/blockquote-dressed variants', pulls='each line under the Authors heading (or the byline content), with list/task/blockquote markup and whitespace stripped', compares_to='at least one non-placeholder named entry must remain'),
    dict(check='authors', sig="unresolved 'will be filled in' placeholder", applies='md', condition="A Technical Report Draft's Authors section is not left on the registry's own tolerated 'Will be filled in' placeholder indefinitely (WARN while still a TRD)", pulls="the Authors heading content (or byline content) when it normalizes to exactly the 'will be filled in' placeholder, on a package classified TRD", compares_to="the existing residue-check precedent (check='residue') tolerating 'Will be filled in' pre-CS, scoped here to the Authors record of an in-progress Technical Report Draft"),
    dict(check='authors', sig="still reads 'will be filled in' on an approved Technical Report", applies='md', condition="An approved (non-draft) Technical Report's Authors section is resolved, not still the 'Will be filled in' placeholder", pulls='the Authors heading content (or byline content) on a package classified as the final Technical Report (not TRD)', compares_to="the TRD-stage 'will be filled in' tolerance does not survive Full Majority Vote approval to the final Technical Report"),
    dict(check='name-chars', sig='must never be used in a filename or directory name that is used in a document URI', applies='both', condition='No underscore in an identifying (document-URI-bearing) package name', pulls="the stage directory name, the version directory name, each stage-root delivery-item filename sharing the package's established basename, and any Multi-Part partN-name directory/file", compares_to="STRICT allowlist [A-Za-z0-9.-]. Naming Directives v1.7 s3: an UNDERSCORE 'must never be used in a filename or directory name that is used in a document URI'"),
    dict(check='name-chars', sig='no exception applies to an identifying package name', applies='both', condition='No character outside the sixty-four permitted characters in an identifying package name', pulls="the stage directory name, the version directory name, each stage-root delivery-item filename sharing the package's established basename, and any Multi-Part partN-name directory/file", compares_to="STRICT allowlist [A-Za-z0-9.-]. Naming Directives v1.7 s3: 'TCs must use only the sixty-four characters from among alphanumerics [A-Za-z0-9] and the two punctuation characters ... PERIOD ... and ... HYPHEN'"),
    dict(check='name-chars', sig='no other character is permitted anywhere in the package', applies='both', condition='No character outside the sixty-four permitted characters plus UNDERSCORE in a supporting (non-identifying) package name', pulls='every filename and directory basename in the package tree outside the identifying set', compares_to="BASE allowlist [A-Za-z0-9._-]. Naming Directives v1.7 s3 base 'must use only' clause, with UNDERSCORE included per the conditional tolerance"),
    dict(check='name-chars', sig='an empty name cannot satisfy it', applies='both', condition='An identifying (document-URI-bearing) package name is non-empty', pulls="the stage directory name, the version directory name, each stage-root delivery-item filename sharing the package's established basename, and any Multi-Part partN-name directory/file", compares_to="STRICT test ^[A-Za-z0-9.-]+$: the '+' quantifier requires at least one character, so an empty identifying name trivially fails the sixty-four-permitted-character allowlist; mirrors how check_stage_name's and check_version_naming's own fullmatch patterns already reject an empty stage/version token without any special-casing"),
    dict(check='extension-count', sig='has no file extension after the document-identifier stem', applies='both', condition='A stage-directory-root delivery item (the established document-identifier stem plus one packaged format) carries at least one file extension', pulls="each delivery-item basename in items, with the 'filenames' check's already-validated shared stem subtracted from the front (only when the basename shares a clean extension boundary with the stem)", compares_to="Naming Directives v1.7 s4: 'A single file(name) extension must be used in each filename except for a recognized set of extensionless filenames in common use.' BLOCKER at published stages, WARN at wd (s5.2 Note: working drafts 'may use any file naming pattern preferred by the TC'); wd-stage match is case-folded.", severity='BLOCKER/WARN'),
    dict(check='extension-count', sig='carries more than one file extension after the stem', applies='both', condition='A stage-directory-root delivery item carries exactly one file extension after the stem (or one blessed compound: tar.gz/tar.bz2/tar.xz, and only when that compound is the WHOLE remaining suffix)', pulls='each delivery-item basename in items, with the shared stem subtracted from the front, split into trailing dot-segments (empty segments from a malformed doubled/trailing dot are preserved, never silently dropped)', compares_to="Naming Directives v1.7 s4's single-extension rule, structurally against the same stem boundary the 'filenames' check already validates. BLOCKER at published stages, WARN at wd.", severity='BLOCKER/WARN'),
    dict(check='extension-count', sig='outside the recognized common-use set', applies='both', condition='A non-delivery-item (Tier B) file with zero dots is one of the three literally recognized extensionless names', pulls="every file basename in the package tree outside the Tier A delivery-item set, junk-files' forbidden names and forbidden directories, and dotfiles", compares_to="Naming Directives v1.7 s9: 'Exceptions to the rule that every filename must include a file extension include: CATALOG or catalog, README, ChangeLog.' Non-blocking WARN per s4's Applicability carve-out for non-identification-pattern files."),
    dict(check='extension-count', sig='commonly denotes a file extension elsewhere', applies='both', condition="A non-delivery-item (Tier B) dotted filename's penultimate segment does not look like a known extension token (or the trailing pair is a blessed compound)", pulls="every dotted file basename in the package tree outside the Tier A delivery-item set, junk-files' forbidden names and forbidden directories, and dotfiles; its last two dot-segments", compares_to="A disclosed, non-exhaustive known-extension-token vocabulary (not an IANA-derived classification); flagged only as a non-blocking heuristic pattern-match advisory per s4's Applicability carve-out for non-identification-pattern files (schemas, images, WSDLs, XML/JSON artifacts)."),
    dict(check='extension-conformance', sig="is not on this check's table of common OASIS publication rendering-format extensions", applies='both', condition='Every root principal/stage-identifying filename and every Multi-Part named-part filename uses an extension that matches a common OASIS publication rendering format', pulls="the file extension token (lowercased, split on the last '.') of every root-level filename that shares the package's known delivery stem, and every filename anywhere in the package whose stem is that same delivery stem plus '-part<N>-<partName>'", compares_to="a curated allowlist of common OASIS document/publication rendering-format extensions (txt, md, html, htm, pdf, doc, docx, odt, ods, odp, xls, xlsx, ppt, pptx, rtf, xml, json, epub), per Naming Directives Section 4 'File extensions should conform to industry best practice, matching well-known IANA MIME Media Types'; filenames on the Section 9 extensionless allowlist (CATALOG, catalog, README, ChangeLog) are exempt"),
    dict(check='artifact-naming', sig='filename embeds a stage/revision token', applies='both', condition="A non-document-identifier artifact's own filename does not embed a stage+revision token", pulls='the full basename of every package file outside the delivery items, the delivery-stem-plus-recognized-suffix set (multi-part -partN-partName / public-review-metadata / comment-resolution-log, each restricted to the extensions a real prose side-file carries), and package-management files (manifest, checksum manifests, exact README/LICENSE variants, _audit/, OS junk)', compares_to="Naming Directives s4: 'it is considered inadvisable to incorporate instance-specific [stage][revision] data for any release in filenames other than in the document identifier files ... thus mySchema.xsd but NOT mySchema-csd02.xsd'; TCs are advised to use named subdirectories and retain stable/identical filenames per s5.2/5.3's stage-abbreviation and two-digit-revision definitions"),
    dict(check='multi-part-naming', sig='inconsistent WP-abbrev tokens', applies='both', condition='Every Multi-Part Work Product part filename embeds the identical WP-abbrev token', pulls='the WP-abbrev token from every stage-root and part-subdirectory filename matching the Multi-Part Naming Directives grammar (<WP-abbrev>-<version-id>-<stage-abbrev><rev>-part<N>-<partName>)', compares_to="the set of distinct WP-abbrev tokens across all matched part filenames must collapse to exactly one value, per TC Process 2.2.3's single Work Product name and the Handbook's Multi-part work products restatement"),
    dict(check='multi-part-naming', sig='inconsistent version-id tokens', applies='both', condition='Every Multi-Part Work Product part filename embeds the identical version-id token', pulls='the version-id token from every stage-root and part-subdirectory filename matching the Multi-Part Naming Directives grammar (<WP-abbrev>-<version-id>-<stage-abbrev><rev>-part<N>-<partName>)', compares_to="the set of distinct version-id tokens across all matched part filenames must collapse to exactly one value, per TC Process 2.2.3's single Work Product version number and the Handbook's Multi-part work products restatement"),
    dict(check='multi-part-naming', sig='bare canonical filename in a multi-part package', applies='both', condition='No bare CORE.ext delivery filename coexists with genuine part files', pulls='delivery-item stems sharing one <wp>-<version>-<stage> core, and their tails', compares_to='naming-directives.txt s4: the single-part bare-CORE filename rule does not apply once the package is multi-part'),
    dict(check='multi-part-naming', sig='missing part identifier', applies='both', condition='Every non-canonical delivery filename sharing the package core carries a well-formed -part<N>-<name> segment', pulls='the tail (text after the resolved <wp>-<version>-<stage> core) of each in-scope delivery filename', compares_to="Naming Directives v1.7 s4 multi-part filename grammar: literal lowercase 'part' + Arabic numeral + hyphen + partName, positioned before the extension"),
    dict(check='multi-part-naming', sig='part filename and containing part-directory disagree', applies='both', condition="A part file discovered inside an Option-1 URI part-subdirectory agrees with that subdirectory's own [partNumber]-[partName] segment", pulls='the part number/name parsed from the filename tail and from its containing part-subdirectory name', compares_to="naming-directives.txt s6.1 (Option 1): the subdirectory segment and the filename's part identifier must name the same part"),
    dict(check='multi-part-naming', sig='part number reused for different parts', applies='both', condition='Each part number maps to exactly one partName across every format variant and discovery location', pulls='the (number, partName) pairs extracted from every in-scope filename tail', compares_to='Naming Directives v1.7 s4: partNumber identifies one distinct separately-titled prose part, not two'),
    dict(check='multi-part-naming', sig='part numbering does not begin at 1', applies='both', condition='Part numbering for a multi-part package begins at 1', pulls="the sorted set of unique part numbers found across the package's in-scope delivery filenames", compares_to="naming-directives.txt s4: partNumber begins with the number '1' (for Part 1)"),
    dict(check='multi-part-naming', sig='part numbering is not monotonically increasing / contains a gap', applies='both', condition='Part numbering for a multi-part package is contiguous with no gaps', pulls="the sorted set of unique part numbers found across the package's in-scope delivery filenames", compares_to='naming-directives.txt s4: partNumber increases monotonically (2, 3, 4, ...) for other parts, i.e. the exact sequence [1, 2, ..., N]'),
    dict(check='public-review-metadata', sig='does not carry the required companion file', applies='both', condition='A live, published csd/cnd stage directory confirmed (by tiered evidence) and successfully scanned to have undergone TC public review carries the required public-review-metadata companion file', pulls="the LIVE docs.oasis-open.org stage-directory-root filename listing (fetched over the network, post-publication audit only), plus a same-revision comment-resolution-log or a downstream cs/errata stage's own Previous-stage cover URL as evidence the review occurred", compares_to="the exact, case-sensitive filename [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber]-public-review-metadata.html (naming-directives.txt 5.2; handbook-Naming.txt 'Public-review metadata filename (new in v1.7)')"),
    dict(check='public-review-metadata', sig='but is empty (0 bytes)', applies='both', condition='A present public-review-metadata companion file is non-empty', pulls='the byte length of the fetched companion file', compares_to="naming-directives.txt 5.2: the file 'provides a publication history of the Work Product' (content validation itself is out of scope for this check; only non-zero size is tested here)"),
    dict(check='public-review-metadata', sig='could not be fetched to confirm its content', applies='both', condition='A public-review-metadata companion file listed in the live directory is actually reachable so its content can be evaluated', pulls='the HTTP status of a direct fetch of the listed companion filename', compares_to='a listing entry alone is not proof of a readable file; an unreachable listed file stays an open advisory rather than a silent, unreviewed pass'),
    dict(check='comment-resolution-log', sig='resembling the required comment-resolution-log is present but misnamed', applies='both', condition='A file resembling a comment-resolution-log, if present in a CSD/CND stage directory that itself carries a public-review-metadata file, carries the exact basename Naming Directives prescribes', pulls="the sibling file listing of the stage directory root (immediate siblings of the document-identifier files only, per naming-directives.txt's 'directory with the CSD or CND' scoping); whether any sibling basename (extension stripped, hyphen/underscore-normalized) contains 'commentresolutionlog' without exactly matching the expected basename under a plausible-format extension", compares_to="the expected basename [stem]-comment-resolution-log against naming-directives.txt s5.2's filename pattern for a produced comment resolution log"),
    dict(check='comment-resolution-log', sig='appears to have concluded', applies='both', condition='Where in-package evidence (a later-stage sibling directory) shows a CSD/CND public review has demonstrably concluded, a comment-resolution-log basename match was sought and not found', pulls='the sibling file listing of the stage directory root; the presence of a later-stage sibling directory (cs/os/errata for a csd gate, cn for a cnd gate) alongside this stage directory, as the review-concluded closure signal', compares_to="tc-process.txt s2.6/s2.7 (comment disposition is required to be posted to the TC's e-mail lists; the downstream approval ballot may only commence once every comment is resolved) against handbook-PublicReviews.txt's 'best practice, not a normative filing mandate' framing for HOW that record is kept"),
    dict(check='normdef-refs', sig='normative-definition file is never referenced from the Work Product', applies='both', condition='Every candidate normative-definition file (schema/grammar/code plain-text file, excluding example/sample/test-case/non-normative and pipeline/asset directories) is referenced from the Work Product', pulls="each candidate file's package-relative path and basename, tested via structured link/href/src/schemaLocation/$ref target extraction (path-level, then basename-level) against the spec's own text (or rendered HTML on the DOCX track), every OTHER candidate file's own content and extracted targets, and manifest.json (package root only)/top-level README-or-index text, all normalized (URL-decode, Unicode NFC)", compares_to="TC Process 2.2.5: 'Each text file must be referenced from the Work Product; and'. Standards Track (csd, cs, os, errata) only"),
    dict(check='normdef-refs', sig='basename-only reference cannot be unambiguously resolved', applies='both', condition='A basename-only match among candidate files sharing that basename in different directories is flagged for confirmation rather than silently satisfying the requirement for every tied file', pulls='candidate files sharing an identical basename in different package directories, and whether any reference to that basename in the corpus is path-qualified', compares_to="TC Process 2.2.5's reference requirement; an ambiguous basename-only match does not unambiguously resolve which file was referenced"),
    dict(check='uri-alias', sig='live <meta http-equiv="refresh">', applies='both', condition='No live META-refresh element in any delivered HTML file', pulls='every <meta> tag in each .html/.htm/.xhtml file, HTML-tokenized (comments/<script>/<style>/<pre>/<code>/<template> excluded)', compares_to='Naming Directives v1.7 s6.5(a): unauthorized URI aliasing via META-refresh elements is barred'),
    dict(check='uri-alias', sig='including a delivery/manifest-cited file', applies='both', condition='No stage-root delivery file or manifest-cited file (by exact package-relative path) shares byte-identical content with another package-relative path', pulls="sha256 of every regular file (symlinks resolved to their in-package target's bytes) in the stage/revision directory", compares_to='Naming Directives v1.7 s6.5(b): preparing files with identical content under two different filenames within a published instance is barred'),
    dict(check='uri-alias', sig='none of which is a delivery/manifest-cited file', applies='both', condition='An ancillary (non-delivery, non-manifest-cited) duplicate is flagged for review, not treated as a s6.5(b) aliasing risk', pulls='sha256 buckets whose members are all non-citable paths (LICENSE/NOTICE/schemas/test-fixtures/asset directories/etc.)', compares_to="the package's own delivery-item paths and manifest.json authoritative/delivery-role paths"),
    dict(check='uri-alias', sig='Previous-stage front-matter cites a redirect', applies='md', condition='The markdown Previous-stage block cites no redirect/URL-shortening domain', pulls="every URL under the 'Previous Stage/Version' heading", compares_to='the seed redirect-service domain list (tinyurl.com, bit.ly, goo.gl, ow.ly, t.co, is.gd, buff.ly, rebrand.ly, tiny.cc, cutt.ly, shorturl.at, rb.gy, purl.oclc.org)'),
    dict(check='uri-alias', sig='DOCX-native cover field cites a redirect', applies='docx', condition="The DOCX-native rendered cover's This/Previous/Latest-version fields cite no redirect/URL-shortening domain", pulls='every URL (visible text or href) between the This/Previous/Latest-version labels on the rendered HTML cover', compares_to='the seed redirect-service domain list'),
    dict(check='uri-alias', sig='names oasis-open.org but links to a redirect', applies='both', condition='Plain-prose anchor text that names oasis-open.org does not link to a redirect/URL-shortening domain', pulls="the visible/anchor text of every [shown](target) (md) or <a>shown</a> (html) construct whose shown text is not itself a URL (a shown-is-a-URL mismatch is the existing link-mismatch check's territory)", compares_to="the seed redirect-service domain list, gated on the anchor text literally containing 'oasis-open.org'", sites=2),
    dict(check='uri-alias', sig='cites oasis-open.org while linking a redirect', applies='both', condition="A bare URL's enclosing sentence that names oasis-open.org does not point at a redirect/URL-shortening domain", pulls='the sentence-bounded prose window (nearest sentence terminator or paragraph break either side) around every bare URL not part of a link construct', compares_to="the seed redirect-service domain list, gated on the sentence window literally containing 'oasis-open.org'", sites=2),
    dict(check='xml-namespace', sig='does not match the required', applies='both', condition="An http(s) namespace's tail matches the docs.oasis-open.org/[tc-shortname]/ns/xxxx pattern", pulls='targetNamespace on the root of each packaged .xsd/.wsdl (incl. wsdl:types-embedded schemas), and the ns attribute on the root grammar/element of each .rng', compares_to="Naming Directives s8 pattern http(s)://docs.oasis-open.org/[tc-shortname]/ns/xxxx, xxxx restricted to the s3 sixty-four-character set plus internal '/', terminating in '/', '#', or alphanumeric; BLOCKER when the tc-shortname has no pattern-grandfather allowlist entry"),
    dict(check='xml-namespace', sig='approval cannot be machine-confirmed', applies='both', condition="A pattern-mismatched namespace's tc-shortname is a confirmed-approved pre-2012 pattern grandfather", pulls='the same pattern-mismatched namespace URI, matched against the pattern-grandfather allowlist', compares_to="Naming Directives v1.2 s9: pre-2012 practice 'may be grandfathered, if approved by Project Administration': WARN when listed but approval is not machine-confirmable at check time"),
    dict(check='xml-namespace', sig='declared under both http and https scheme', applies='both', condition='The same namespace tail is declared under one scheme only, package-wide', pulls='every http(s) namespace URI declared by any packaged .xsd/.wsdl(+embedded)/.rng in the package, grouped by scheme-stripped tail', compares_to='Naming Directives s8: \'While either "http" or "https" may be used ... they are not interchangeable. One or the other must be used consistently.\''),
    dict(check='xml-namespace', sig='not on the URN-grandfather allowlist', applies='both', condition="A urn:-scheme declared namespace's TC is on the URN-grandfather allowlist", pulls='the urn:-scheme namespace URI and its owning tc-shortname', compares_to="Naming Directives s8: URN-based namespaces 'must not be declared otherwise', permitted only for TCs that already used the feature (or Maintenance Activity TCs), approved by Project Administration"),
    dict(check='xml-namespace', sig='not evaluated by this check -- manual review', applies='both', condition='A RELAX NG grammar declares only one namespace, on its root grammar/element node', pulls="every ns attribute on non-root nodes of a .rng file, compared to the root node's ns", compares_to='this check only validates the root-level self-declared namespace; a differing non-root ns is flagged for manual review rather than silently dropped'),
    dict(check='ns-segment', sig='reuses the reserved /ns/ segment', applies='both', condition='This-stage and Latest-stage cover URIs do not reuse the reserved /ns/ path segment', pulls='the This-stage and Latest-stage URL(s) from the markdown front matter (md track) or the rendered HTML cover (docx-native track, via the shared html_cover_urls() helper)', compares_to="handbook-Naming.txt: '/ns/ ... is for namespace identifiers, not for retrievable documents. Do not use /ns/ in the URI of a document you intend to publish as a retrievable resource'"),
    dict(check='ns-segment', sig='cited as the immediately-preceding-stage document', applies='both', condition='Previous-stage cover URI does not reuse the reserved /ns/ path segment (non-blocking, manual-review if it does: an immutable inherited citation)', pulls='the Previous-stage URL from the markdown front matter (md track) or the rendered HTML cover (docx-native track, via the shared html_cover_urls() helper)', compares_to="handbook-Naming.txt's /ns/ reservation rule, applied to an already-published prior-stage citation the current package cannot alter"),
]


def conditions_inventory() -> list[dict]:
    """Join the AST's defect-condition sites with CONDITION_DOCS and assert
    they agree in both directions. Returns one entry per individual condition
    (a doc with sites=N expands to N entries), each carrying the doc fields."""
    import ast as _ast
    tree = _ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    sites = []
    for node in _ast.walk(tree):
        if (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
                and node.func.attr == "add" and len(node.args) >= 3):
            sev = getattr(node.args[0], "id", "")
            if sev == "INFO":
                continue
            cid = node.args[1].value if isinstance(node.args[1], _ast.Constant) else "(dynamic)"

            def constants(n) -> list[str]:
                if isinstance(n, _ast.Constant):
                    return [str(n.value)]
                if isinstance(n, _ast.JoinedStr):
                    return [str(v.value) for v in n.values if isinstance(v, _ast.Constant)]
                if isinstance(n, _ast.BinOp):
                    return constants(n.left) + constants(n.right)
                if isinstance(n, _ast.IfExp):
                    return constants(n.body) + constants(n.orelse)
                return []

            template = "".join(constants(node.args[2]))
            if template.startswith("..."):
                continue
            sites.append({"check": cid, "template": template,
                          "severity": sev, "lineno": node.lineno})
    matched: dict[int, dict] = {}
    for doc in CONDITION_DOCS:
        hits = [s for s in sites if s["check"] == doc["check"] and doc["sig"] in s["template"]]
        want = doc.get("sites", 1)
        if len(hits) != want:
            raise AssertionError(
                f"condition registry drift: ({doc['check']!r}, {doc['sig']!r}) matches "
                f"{len(hits)} AST site(s), expected {want}")
        for h in hits:
            if id(h) in matched:
                raise AssertionError(
                    f"condition registry overlap: AST site at line {h['lineno']} matched by "
                    f"both {matched[id(h)]['sig']!r} and {doc['sig']!r}")
            matched[id(h)] = doc
    unmatched = [s for s in sites if id(s) not in matched]
    if unmatched:
        raise AssertionError(
            "undocumented condition site(s): " +
            "; ".join(f"line {s['lineno']} [{s['check']}] {s['template'][:60]!r}" for s in unmatched))
    out = []
    for doc in CONDITION_DOCS:
        hits = sorted((s for s in sites if matched.get(id(s)) is doc), key=lambda s: s["lineno"])
        for i, h in enumerate(hits):
            entry = {k: v for k, v in doc.items() if k != "sites"}
            # AST severity when the call site names a literal token; a
            # dynamic site (e.g. `sev = BLOCKER if ... else WARN`) must
            # declare its range in the registry entry instead.
            if h["severity"] in ("BLOCKER", "WARN"):
                entry["severity"] = h["severity"]
            elif "severity" not in entry:
                raise AssertionError(
                    f"dynamic severity at line {h['lineno']} [{doc['check']}] "
                    f"needs an explicit severity in its registry entry")
            if doc.get("sites", 1) > 1:
                entry = dict(entry)
                entry["condition"] += (" (markdown source)" if i == 0 else " (HTML render)")
            out.append(entry)
    return out


def list_checks() -> int:
    """Self-introspect: parse this file's AST and count every individual
    defect condition (each BLOCKER/WARN finding site; continuation lines and
    INFO notes excluded). The advertised numbers are asserted from the code,
    never hand-counted in prose -- prose drifts, the AST does not."""
    import ast as _ast
    from collections import Counter
    tree = _ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    per_class: Counter = Counter()
    for node in _ast.walk(tree):
        if (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
                and node.func.attr == "add" and len(node.args) >= 3):
            sev = getattr(node.args[0], "id", "")
            if sev == "INFO":
                continue
            cid = node.args[1].value if isinstance(node.args[1], _ast.Constant) else "(dynamic)"
            msg = node.args[2]
            first = ""
            if isinstance(msg, _ast.Constant):
                first = str(msg.value)
            elif isinstance(msg, _ast.JoinedStr) and msg.values and isinstance(msg.values[0], _ast.Constant):
                first = str(msg.values[0].value)
            if first.startswith("..."):
                continue  # overflow/continuation message, not a distinct condition
            per_class[cid] += 1
    total = sum(per_class.values())
    width = max(len(c) for c in per_class)
    for cid, n in sorted(per_class.items()):
        print(f"  {cid:{width}}  {n}")
    print(f"\n{total} individual checks across {len(per_class)} check classes.")
    inv = conditions_inventory()   # raises on registry/AST drift
    assert len(inv) == total, f"registry expands to {len(inv)} conditions, AST counts {total}"
    print(f"condition registry: {len(inv)} documented conditions, in sync with the AST.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", nargs="?", help="stage directory or package .zip")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--emit-manifest", action="store_true",
                    help="write manifest.json (sha256, source commit, tool versions) into the "
                         "stage dir before checking")
    ap.add_argument("--list-checks", action="store_true",
                    help="print every check class with its individual-condition count "
                         "(AST-derived from this file; the source of the advertised numbers)")
    args = ap.parse_args()

    if args.list_checks:
        return list_checks()
    if not args.target:
        ap.error("target is required unless --list-checks is given")

    f = Findings()
    tmp = None
    # resolve to absolute: stage/version tokens are derived from path segments,
    # and a relative target ('.', 'cnd01') yields empty tokens and false blockers
    target = os.path.abspath(args.target)
    if target.endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="pub_check_")
        try:
            with zipfile.ZipFile(target) as z:
                for name in z.namelist():
                    dest = os.path.realpath(os.path.join(tmp, name))
                    if not dest.startswith(os.path.realpath(tmp) + os.sep):
                        print(f"error: zip entry escapes extraction dir: {name}",
                              file=sys.stderr)
                        return 2
                z.extractall(tmp)
        except zipfile.BadZipFile as e:
            print(f"error: not a readable zip: {e}", file=sys.stderr)
            return 2
        target = locate_stage_dir(tmp)
    if not os.path.isdir(target):
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2

    if args.emit_manifest:
        version, stage = parse_stage(target)
        print(f"wrote {emit_manifest(target, version, stage)}")
        print(f"wrote {emit_manifest_txt(target, version, stage)}")

    run(target, f)

    if args.json:
        print(json.dumps({"target": args.target, "findings": f.items,
                          "blockers": f.blockers,
                          "conditions": conditions_inventory(),
                          "observed": f.observed}, indent=2))
    else:
        # Aggregate repeated same-class warnings so blockers stay readable:
        # 102 case warnings on one KMIP package drowned 3 blockers (Jul 2026).
        # --json always carries the full list.
        by_group: dict[tuple[str, str], list[dict]] = {}
        for item in f.items:
            by_group.setdefault((item["severity"], item["check"]), []).append(item)
        display: list[dict] = []
        for (sev, check), group in by_group.items():
            if sev == WARN and len(group) > 5:
                display.extend(group[:3])
                display.append({"severity": WARN, "check": check,
                                "message": f"...and {len(group) - 3} more '{check}' "
                                           f"warnings (--json lists all)."})
            else:
                display.extend(group)
        order = {BLOCKER: 0, WARN: 1, INFO: 2}
        for item in sorted(display, key=lambda x: order[x["severity"]]):
            print(f"[{item['severity']:7}] {item['check']:13} {item['message']}")
        n_warn = sum(1 for x in f.items if x["severity"] == WARN)
        verdict = "NOT PUBLISHABLE" if f.blockers else "publishable"
        print(f"\n{f.blockers} blocker(s), {n_warn} warning(s) -> {verdict}")

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if f.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
