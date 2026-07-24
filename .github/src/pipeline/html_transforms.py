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

"""The OASIS HTML post-processing chain, one class per transform.

Each fix-up documented in ``TRANSFORMS.md`` is an :class:`HtmlTransform`
subclass. The contractual order lives in ONE place —
:attr:`pipeline.html_converter.HtmlConverter.TRANSFORMS` — as an ordered
tuple of these classes, so the chain is introspectable, unit-testable per
transform, and extensible by subclassing the converter instead of editing a
monolithic method.

Every transform receives the parsed soup and the owning
:class:`~pipeline.html_converter.HtmlConverter` (its document context:
canonical URLs, output paths, extracted metadata). A transform returns the
soup it worked on — or a NEW soup when its work forces a re-parse
(:class:`LinkifyPlainUrls` round-trips through text by design).
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests.exceptions import RequestException

if TYPE_CHECKING:  # circular-import guard: the converter imports this module
    from .html_converter import HtmlConverter

logger = logging.getLogger(__name__)


def _is_tag(n: object) -> bool:
    """Return True if ``n`` is a BeautifulSoup :class:`~bs4.Tag` node."""
    return isinstance(n, Tag)


class HtmlTransform(ABC):
    """One named, ordered element of the post-processing chain."""

    #: kebab-case identifier used in logs and in TRANSFORMS.md cross-references
    name: str = ""

    @abstractmethod
    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        """Apply this transform and return the soup (new or mutated in place)."""
        raise NotImplementedError


class _LogoAware:
    """Shared logo-recognition behavior for the transforms that police the
    OASIS cover logo. Inherit alongside :class:`HtmlTransform`."""

    @staticmethod
    def first_tag_child(parent: Tag) -> Tag | None:
        """Return the first child of ``parent`` that is a Tag, or None."""
        for c in parent.children:
            if isinstance(c, Tag):
                return c
        return None

    @staticmethod
    def looks_like_logo_src(ctx: "HtmlConverter", src: str) -> bool:
        """Return True if ``src`` appears to reference the OASIS logo image."""
        if not src:
            return False
        return (
            "OASISLogo-v3.0.png" in src
            or src == ctx.logo_canonical_remote
            or bool(ctx.logo_ok_src_regex.match(src))
        )

    def is_canonical_logo_img(self, ctx: "HtmlConverter", img: Tag, body: Tag) -> bool:
        """Return True if ``img`` is the single canonical top-of-body logo."""
        if img.name != "img":
            return False
        src = (img.get("src") or "").strip()
        alt = (img.get("alt") or "").strip()
        if not (self.looks_like_logo_src(ctx, src) and alt == "OASIS Logo"):
            return False
        parent = img.parent
        if not (parent and parent.name == "p" and parent.parent is body):
            return False
        return parent is self.first_tag_child(body)


class StripPandocHeader(HtmlTransform):
    """Remove pandoc's ``<header id="title-block-header">`` block."""

    name = "strip-pandoc-header"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        if soup.header:
            soup.header.decompose()
        return soup


class InjectMetaDescription(HtmlTransform):
    """Insert the ``<meta name="description">`` extracted from the Markdown."""

    name = "inject-meta-description"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        meta_tag = soup.new_tag(
            "meta", attrs={"name": "description", "content": ctx.meta_description}
        )
        soup.head.insert(0, meta_tag)
        return soup


class RemoveBaseHref(HtmlTransform):
    """Drop any ``<base>`` tag: it breaks fragment-only TOC navigation."""

    name = "remove-base-href"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        base_tag = soup.find("base")
        if base_tag:
            base_tag.decompose()
            logger.debug("Removed base tag to fix internal fragment links")
        return soup


class DropLogoFigures(_LogoAware, HtmlTransform):
    """Remove ``<figure>`` wrappers pandoc puts around the OASIS logo (the
    figcaption renders the alt text as visible caption)."""

    name = "drop-logo-figures"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        for fig in list(soup.find_all("figure")):
            img = fig.find("img")
            if img and self.looks_like_logo_src(ctx, img.get("src", "")):
                fig.decompose()
        return soup


class DropNavBlocks(HtmlTransform):
    """Kill stray TOC ``<nav>`` blocks; the document carries its own TOC."""

    name = "drop-nav-blocks"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        if soup.nav:
            soup.nav.decompose()
        return soup


class EnforceSingleLogo(_LogoAware, HtmlTransform):
    """Ensure exactly one canonical OASIS logo, as the first body element."""

    name = "enforce-single-logo"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        body = soup.body or soup
        self._drop_non_canonical(soup, ctx, body)
        first_el = self.first_tag_child(body)
        current_good = None
        if first_el and first_el.name == "p":
            maybe_img = first_el.find("img", recursive=False) or first_el.find("img")
            if maybe_img and self.is_canonical_logo_img(ctx, maybe_img, body):
                current_good = first_el
        if not current_good:
            self._install_canonical(soup, ctx, body)
        self._drop_non_canonical(soup, ctx, body)
        return soup

    def _drop_non_canonical(self, soup: BeautifulSoup, ctx: "HtmlConverter",
                            body: Tag) -> None:
        """Remove every logo-looking image that is not THE canonical one."""
        for img in list(soup.find_all("img")):
            src = img.get("src") or ""
            alt = img.get("alt") or ""
            if ("OASISLogo" in src) or (alt.strip() == "OASIS Logo"):
                if not self.is_canonical_logo_img(ctx, img, body):
                    p = img.parent
                    if p and p.name == "p" and all(
                        (isinstance(x, Tag) and x.name == "img") or str(x).strip() == ""
                        for x in p.contents
                    ):
                        p.decompose()
                    else:
                        img.decompose()

    def _install_canonical(self, soup: BeautifulSoup, ctx: "HtmlConverter",
                           body: Tag) -> None:
        """Promote an existing good logo to the top of body, or create one."""
        existing_good_img = None
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            alt = img.get("alt") or ""
            if self.looks_like_logo_src(ctx, src) and alt == "OASIS Logo":
                existing_good_img = img
                break
        if existing_good_img:
            container = (
                existing_good_img.parent
                if (existing_good_img.parent and existing_good_img.parent.name == "p")
                else None
            )
            if not container:
                container = soup.new_tag("p")
                existing_good_img.replace_with(container)
                container.append(existing_good_img)
            first_tag = self.first_tag_child(body)
            if first_tag:
                first_tag.insert_before(container)
            else:
                body.insert(0, container)
        else:
            p = soup.new_tag("p")
            img = soup.new_tag("img", src=ctx.logo_canonical_remote, alt="OASIS Logo")
            p.append(img)
            first_tag = self.first_tag_child(body)
            if first_tag:
                first_tag.insert_before(p)
            else:
                body.insert(0, p)


class FixTopBanner(_LogoAware, HtmlTransform):
    """Normalize the logo/title banner: drop stray ``<hr>``, add a styled one,
    and promote the first ``<h1>`` to ``<h1big>`` to avoid a premature break."""

    name = "fix-top-banner"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        body = soup.body or soup
        logo_p = None
        for p_tag in body.find_all("p", recursive=False):
            img = p_tag.find("img", recursive=False)
            if img and self.is_canonical_logo_img(ctx, img, body):
                logo_p = p_tag
                break
        if not logo_p:
            logger.warning(
                "Could not find the canonical OASIS logo paragraph. Skipping banner fix."
            )
            return soup
        first_heading = None
        for sibling in logo_p.find_next_siblings():
            if _is_tag(sibling) and sibling.name in (
                "h1", "h1big", "h2", "h3", "h4", "h5", "h6"
            ):
                first_heading = sibling
                break
        if not first_heading:
            logger.warning(
                "Could not find a heading after the OASIS logo. Skipping banner fix."
            )
            return soup
        node = logo_p.next_sibling
        while node and node != first_heading:
            if _is_tag(node) and node.name == "hr":
                next_node = node.next_sibling
                logger.debug("Removing extraneous <hr> tag between logo and title.")
                node.decompose()
                node = next_node
            else:
                node = node.next_sibling
        next_elem = logo_p.next_sibling
        while next_elem and not _is_tag(next_elem):
            next_elem = next_elem.next_sibling
        if not (
            next_elem
            and next_elem.name == "hr"
            and "page-break-before: avoid" in next_elem.get("style", "")
        ):
            if next_elem != first_heading:
                styled_hr = soup.new_tag("hr")
                styled_hr["style"] = "page-break-before: avoid"
                logo_p.insert_after(styled_hr)
        if first_heading.name == "h1":
            logger.debug(
                "Upgrading first <h1> to <h1big> to prevent premature page break."
            )
            first_heading.name = "h1big"
        return soup


class RemoveDuplicateHeadingAnchors(HtmlTransform):
    """Drop anchor tags inside a heading that duplicate the heading's own id."""

    name = "remove-duplicate-heading-anchors"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        for heading in soup.find_all(["h1", "h1big", "h2", "h3", "h4", "h5", "h6"]):
            heading_id = heading.get("id")
            if heading_id:
                for anchor in heading.find_all("a", id=heading_id):
                    logger.debug(
                        "Removing duplicate anchor with id='%s' from heading", heading_id
                    )
                    if anchor.string:
                        anchor.replace_with(anchor.string)
                    else:
                        anchor.decompose()
        return soup


class NormalizeSameDocAnchors(HtmlTransform):
    """Rewrite links that target this same document to fragment-only hrefs, so
    the TOC works both as a local file and under the published URL."""

    name = "normalize-same-doc-anchors"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        output_basename = os.path.basename(ctx.output_file)
        for a in soup.find_all("a", href=True):
            href = (a["href"] or "").strip()
            if not href:
                continue
            if href.startswith("#"):
                a.attrs.pop("target", None)
                continue
            p = urlparse(href)
            if not p.fragment:
                continue
            same_doc = False
            if not p.scheme and not p.netloc:
                if (p.path == "") or (os.path.basename(p.path) == output_basename):
                    same_doc = True
            else:
                if os.path.basename(p.path) == output_basename:
                    same_doc = True
            if same_doc:
                new_href = f"#{p.fragment}"
                logger.debug(
                    "Normalizing same-document anchor: '%s' -> '%s'", href, new_href
                )
                a["href"] = new_href
                a.attrs.pop("target", None)
        return soup


class LinkifyPlainUrls(HtmlTransform):
    """Wrap bare ``http(s)`` URLs in tag-free paragraphs as ``<a>`` links.

    Works on serialized text, so it returns a NEW soup: the chain contract
    (apply returns the soup to continue with) exists for exactly this case."""

    name = "linkify-plain-urls"

    _url_re = re.compile(r"(https?://[^\s<]+)")

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        for p in soup.find_all("p"):
            if p.find(True):
                continue  # already has tags
            text = p.get_text()
            if "http" not in text:
                continue
            new_html = self._url_re.sub(
                lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', text
            )
            p.clear()
            p.append(BeautifulSoup(new_html, "html.parser"))
        return BeautifulSoup(str(soup), "html.parser")


class LocalizeCss(HtmlTransform):
    """Download remote stylesheets next to the HTML (opt-in via
    ``HTML_LOCALIZE_CSS``) and repoint the ``<link>`` tags."""

    name = "localize-css"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        if os.getenv("HTML_LOCALIZE_CSS", "").lower() not in {"1", "true", "yes"}:
            return soup
        ctx.mkdirp(ctx.styles_dir)
        for link in list(soup.find_all("link", rel=True, href=True)):
            if (link.get("rel") or [""])[0].lower() != "stylesheet":
                continue
            href = link["href"].strip()
            pr = urlparse(href)
            if pr.scheme in {"http", "https"}:
                css_name = os.path.basename(pr.path) or "style.css"
                local_css = os.path.join(ctx.styles_dir, css_name)
                if not os.path.exists(local_css):
                    try:
                        logger.info("Downloading CSS %s -> %s", href, local_css)
                        r = requests.get(href, timeout=10)
                        r.raise_for_status()
                        with open(local_css, "wb") as f:
                            f.write(r.content)
                    except RequestException:
                        logger.error("Failed to download CSS: %s", href, exc_info=True)
                        continue
                link["href"] = os.path.join(ctx.styles_subdir, css_name)
        return soup


class LocalizeImages(HtmlTransform):
    """Download remote images into ``images/`` and repoint ``src`` (dropping
    ``srcset``); an image that cannot be fetched is removed rather than
    shipped broken."""

    name = "localize-images"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        for img in list(soup.find_all("img", src=True)):
            src = img["src"].strip()
            pr = urlparse(src)
            if pr.scheme in {"http", "https"}:
                image_filename = os.path.basename(pr.path) or "image"
                local_image_path = os.path.join(ctx.images_dir, image_filename)
                if not os.path.exists(local_image_path):
                    try:
                        logger.info("Downloading image %s -> %s", src, local_image_path)
                        r = requests.get(src, timeout=10)
                        r.raise_for_status()
                        with open(local_image_path, "wb") as f:
                            f.write(r.content)
                    except RequestException:
                        logger.error("Failed to download image %s", src, exc_info=True)
                        img.decompose()
                        continue
                img["src"] = os.path.join(ctx.images_subdir, image_filename)
                if img.has_attr("srcset"):
                    del img["srcset"]
        return soup


class RelativizeSameScopeLinks(HtmlTransform):
    """Rewrite in-scope absolute links/refs/srcs to document-relative paths."""

    name = "relativize-same-scope-links"

    def apply(self, soup: BeautifulSoup, ctx: "HtmlConverter") -> BeautifulSoup:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#"):
                continue
            tail = ctx.path_tail_if_same_scope(href)
            if not tail:
                continue
            pp = urlparse(href)
            if os.path.basename(pp.path) == os.path.basename(ctx.output_file):
                if pp.fragment:
                    a["href"] = f"#{pp.fragment}"
                else:
                    a["href"] = os.path.basename(pp.path)
                a.attrs.pop("target", None)
            else:
                a["href"] = tail.lstrip("/")
        for link in soup.find_all("link", href=True):
            tail = ctx.path_tail_if_same_scope(link["href"].strip())
            if tail:
                link["href"] = tail.lstrip("/")
        for s in soup.find_all("script", src=True):
            tail = ctx.path_tail_if_same_scope(s["src"].strip())
            if tail:
                s["src"] = tail.lstrip("/")
        for img in soup.find_all("img", src=True):
            tail = ctx.path_tail_if_same_scope(img["src"].strip())
            if tail:
                img["src"] = tail.lstrip("/")
        return soup
