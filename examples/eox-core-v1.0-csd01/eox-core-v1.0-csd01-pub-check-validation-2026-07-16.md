# Publication Validation Report (pub-check): OpenEoX Core Schema Version 1.0 CSD01

**TC:** openeox  
**Stage:** csd01  
**Target:** https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/ (as-published tree, OASIS-Docs/openeox HEAD)  
**Ticket:** TCADMIN-4725  
**Validation date:** 2026-07-16  
**Tool:** oasis_pub_check.py (OASIS-Docs/publication-assurance)  
**Coverage:** 92 individual checks across 34 check classes, all run  
**Blockers:** 0  

**Result: PUBLICATION-READY: zero blockers.** 26 of 34 check classes fully clean; findings: 0 error, 9 warning, 3 informational.

Triage: this validation ran against the ALREADY-PUBLISHED csd01 tree, so the revision-collision warnings record the tool correctly seeing this same publication live (expected in a post-publication run, not a defect). The front-matter version warnings are intentional external references to the CSAF v2.1 specification. The 'Will be filled in' acknowledgment placeholders were shipped deliberately by the TC for this early stage and must be resolved before CS. Zero blockers: the package is publication-ready and was published 13 July 2026.

| # | Result | Check class | Conditions | Findings |
|---|---|---|---|---|
| 1 | PASS | asset-refs | 1 | none |
| 2 | PASS | case | 3 | none |
| 3 | WARN | cover-hr | 1 | WARN: Horizontal rule between the OASIS logo and the title: the publication CSS treats <hr/> as a page break, which opens the PDF with a blank page. Harmless in other renderers; remove if publishing through the OASIS HTML-to-PDF path. |
| 4 | PASS | date-sync | 2 | none |
| 5 | PASS | dead-lists | 3 | none |
| 6 | PASS | double-slash | 1 | none |
| 7 | PASS | fence-collapse | 1 | none |
| 8 | PASS | filenames | 6 | none |
| 9 | WARN | front-matter | 12 | WARN: URL declares version v2.1 (package is v1.0): https://docs.oasis-open.org/csaf/csaf/v2.1/csaf-v2.1.html -- confirm this is an intentional external reference.<br>WARN: URL declares version v2.1 (package is v1.0): https://docs.oasis-open.org/csaf/csaf/v2.1/csd01/csaf-v2.1-csd01.html -- confirm this is an intentional external reference. |
| 10 | PASS | generator | 1 | none |
| 11 | PASS | html-anchors | 2 | none |
| 12 | PASS | html-residue | 3 | none |
| 13 | PASS | html-title | 2 | none |
| 14 | PASS | image-policy | 10 | none |
| 15 | PASS | junk-files | 2 | none |
| 16 | PASS | link-mismatch | 1 | none |
| 17 | PASS | logo | 1 | none |
| 18 | INFO | manifest | 3 | INFO: No manifest.json in the package. Emit one (--emit-manifest or your own tool) and intake verification becomes automatic. |
| 19 | WARN | md-links | 2 | WARN: Dual link [url](url); prefer a bare URL (autolinked) or real anchor text: https://www.oasis-open.org/committees/openeox/ipr.php<br>WARN: Dual link [url](url); prefer a bare URL (autolinked) or real anchor text: https://www.oasis-open.org/policies-guidelines/trademark/ |
| 20 | PASS | package-refs | 1 | none |
| 21 | PASS | pdf-cover | 2 | none |
| 22 | WARN | pdf-fonts | 2 | WARN: PDF embeds fonts not declared by the package's own CSS: LibertinusSerif, NewCM10, NewCMMath. The CSS declares: couriernew, liberationsans. Confirm the divergence is intentional (pdffonts <file.pdf> re-checks this after a toolchain change). |
| 23 | PASS | pdf-sync | 5 | none |
| 24 | PASS | previous-stage | 2 | none |
| 25 | WARN | residue | 3 | WARN: 'Will be filled in …' placeholder present in markdown (acceptable for an early stage; must be resolved before CS).<br>WARN: 'Will be filled in …' placeholder present in html (acceptable for an early stage; must be resolved before CS). |
| 26 | WARN | revision-collision | 1 | WARN: Stage /csd01/ is already published at https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/: a NEW submission for v1.0 must use the next revision number instead. Ignore this warning if you are re-checking the published package itself.<br>INFO: Published stages already live under https://docs.oasis-open.org/openeox/eox-core/v1.0/: csd01. |
| 27 | PASS | rfc-keywords | 2 | none |
| 28 | PASS | schema-id | 4 | none |
| 29 | PASS | stage-name | 3 | none |
| 30 | PASS | symlinks | 1 | none |
| 31 | PASS | template | 3 | none |
| 32 | INFO | template-css | 2 | INFO: HTML ships its own stylesheet rather than the canonical markdown-styles CSS; fonts match the template family. Accepted practice (OpenEoX publishes this way), noting it for the record. |
| 33 | PASS | version-naming | 3 | none |
| 34 | PASS | vml-fallback | 1 | none |

## All Individual Conditions: Observed vs Expected

| # | Result | Check | Condition verified | Value pulled (observed) | Compared against |
|---|---|---|---|---|---|
| 1 | PASS | stage-name | Stage directory name carries a two-digit revision number | stage_directory: csd01 | valid stage prefixes must carry a two-digit suffix (csd01, never bare csd) |
| 2 | PASS | stage-name | Stage token is not a retired abbreviation | stage_directory: csd01 | retired token set (csprd, cnprd, cos, csdpr, cndpr) per Naming Directives v1.7 |
| 3 | PASS | stage-name | Stage token is a recognized current stage | stage_directory: csd01 | valid stage set: wd, csd, cs, cnd, cn, os, ps, psd, pn, pnd, errata |
| 4 | PASS | version-naming | Version directory matches the vN.N(.N) convention | version_directory: v1.0; delivery_stem: eox-core-v1.0-csd01 | the Naming Directives version-segment pattern vN.N(.N), e.g. v1.0, v2.0.1 |
| 5 | PASS | version-naming | Version embedded in the delivery filename agrees with the version directory | version_directory: v1.0; delivery_stem: eox-core-v1.0-csd01 | the version directory the package publishes under |
| 6 | PASS | version-naming | Delivery filename embeds the version segment | version_directory: v1.0; delivery_stem: eox-core-v1.0-csd01 | the Naming Directives filename shape <base>-<version>-<stage> |
| 7 | WARN | revision-collision | The submitted stage does not already exist on the live site | Stage /csd01/ is already published at https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/: a NEW submission for v1.0 must use the next revision number instead. Ignore this warning if you are re-checking the published package itself. | expected non-200 for a NEW submission; an existing stage means the revision must increment |
| 8 | PASS | filenames | The stage directory contains delivery items at all | stems: eox-core-v1.0-csd01; delivery_files: eox-core-v1.0-csd01.html, eox-core-v1.0-csd01.md, eox-core-v1.0-csd01.pdf; formats_present: html, md, pdf; required_formats: html, md, pdf | at least one delivery item (md/docx/odt/html/pdf) must be present |
| 9 | PASS | filenames | All delivery items share one basename | stems: eox-core-v1.0-csd01; delivery_files: eox-core-v1.0-csd01.html, eox-core-v1.0-csd01.md, eox-core-v1.0-csd01.pdf; formats_present: html, md, pdf; required_formats: html, md, pdf | exactly one distinct stem across md/docx/odt/html/pdf |
| 10 | PASS | filenames | Delivery filename carries no working token | stems: eox-core-v1.0-csd01; delivery_files: eox-core-v1.0-csd01.html, eox-core-v1.0-csd01.md, eox-core-v1.0-csd01.pdf; formats_present: html, md, pdf; required_formats: html, md, pdf | forbidden working tokens: draft, tmp, rc (files are named for the published stage) |
| 11 | PASS | filenames | Delivery filename ends in the stage suffix | stems: eox-core-v1.0-csd01; delivery_files: eox-core-v1.0-csd01.html, eox-core-v1.0-csd01.md, eox-core-v1.0-csd01.pdf; formats_present: html, md, pdf; required_formats: html, md, pdf | the stage directory name as a -<stage> suffix |
| 12 | PASS | filenames | All required delivery formats are present | stems: eox-core-v1.0-csd01; delivery_files: eox-core-v1.0-csd01.html, eox-core-v1.0-csd01.md, eox-core-v1.0-csd01.pdf; formats_present: html, md, pdf; required_formats: html, md, pdf | the track's required set: html+pdf plus the authoritative source (md, docx, or odt) |
| 13 | PASS | filenames | An authoritative source artifact travels with the renderings | stems: eox-core-v1.0-csd01; delivery_files: eox-core-v1.0-csd01.html, eox-core-v1.0-csd01.md, eox-core-v1.0-csd01.pdf; formats_present: html, md, pdf; required_formats: html, md, pdf | at least one authoritative source (.md, .docx, or .odt) expected beside HTML/PDF |
| 14 | PASS | front-matter | Markdown front matter carries a This-stage URL block | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | at least one URL must be declared |
| 15 | PASS | front-matter | Every stage URL is under docs.oasis-open.org | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | the canonical site prefix https://docs.oasis-open.org/ |
| 16 | PASS | front-matter | This-stage URLs carry the version and stage path segments | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | the package's /<version>/ and /<stage>/ path segments |
| 17 | PASS | front-matter | Every This-stage URL points at a file shipped in the package | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | the set of delivery filenames actually in the package |
| 18 | PASS | front-matter | The This-stage block lists all three artifacts (md, html, pdf) | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | the full delivery set: .md, .html, .pdf |
| 19 | PASS | front-matter | Latest-stage URLs point at the persistent version root | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | must NOT contain the /<stage>/ segment (latest is the version-root path) |
| 20 | PASS | front-matter | Latest-stage URLs are under the package's version directory | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | the package's /<version>/ path segment |
| 21 | WARN x2 | front-matter | Any docs.oasis-open.org URL declaring a different version is intentional | URL declares version v2.1 (package is v1.0): https://docs.oasis-open.org/csaf/csaf/v2.1/csaf-v2.1.html -- confirm this is an intentional external reference. | URL declares version v2.1 (package is v1.0): https://docs.oasis-open.org/csaf/csaf/v2.1/csd01/csaf-v2.1-csd01.html -- confirm this is an intentional external reference. | the package's own version; a different version is a stale-draft tell unless external |
| 22 | PASS | front-matter | No Latest-labelled line cites a stage-pinned URL for this spec | this_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.pdf; latest_stage_urls: https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.html, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.md, https://docs.oasis-open.org/openeox/eox-core/v1.0/eox-core-v1.0.pdf | the persistent version-root form (no /<stage>/ segment) |
| 23 | NA | front-matter | HTML cover carries a This-version URL block | NA: DOCX-render condition; this package carries no Word source | at least one URL must be present |
| 24 | NA | front-matter | Cover This-version URLs carry the version and stage segments | NA: DOCX-render condition; this package carries no Word source | the package's /<version>/ and /<stage>/ path segments |
| 25 | NA | front-matter | Cover Latest-version URLs point at the persistent version root | NA: DOCX-render condition; this package carries no Word source | must NOT contain the /<stage>/ segment |
| 26 | PASS | residue | No editor TODO markers left in prose | scanned: html, markdown | the patterns TODO(...) and TODO: must not occur |
| 27 | PASS | residue | No bare 'tbd' placeholder sections | scanned: html, markdown | no line consisting solely of 'tbd' |
| 28 | WARN x2 | residue | No 'Will be filled in' placeholders (early-stage tolerated, must resolve before CS) | 'Will be filled in …' placeholder present in markdown (acceptable for an early stage; must be resolved before CS). | 'Will be filled in …' placeholder present in html (acceptable for an early stage; must be resolved before CS). | the phrase 'Will be filled in' must not occur |
| 29 | PASS | html-title | HTML title carries no working residue | title: OpenEoX Core Schema Version 1.0 | must not end in tmp, draft, or wip |
| 30 | PASS | html-title | HTML title is a plausible document title | title: OpenEoX Core Schema Version 1.0 | a full spec title (at least 8 characters) |
| 31 | PASS | html-residue | No stale pandoc title-block header in the HTML | title_block_headers: 0; runner_paths: 0 | the <header id="title-block-header"> element must be absent (lint D2) |
| 32 | PASS | html-residue | No CI runner paths in HTML hrefs or srcs | title_block_headers: 0; runner_paths: 0 | the /home/runner/ path prefix must not occur (lint D3) |
| 33 | PASS | html-residue | The document title appears in exactly one H1 | title_block_headers: 0; runner_paths: 0 | exactly 1 (more renders the title twice on the PDF cover, lint D1) |
| 34 | PASS | html-anchors | Every internal fragment link resolves to an anchor | internal_links: 91; anchors: 273; unresolved: 0 | every referenced fragment must exist as an id or <a name> |
| 35 | PASS | html-anchors | The HTML carries a linked table of contents | internal_links: 91; anchors: 273; unresolved: 0 | at least one expected (a spec HTML without any is missing its TOC links) |
| 36 | WARN x2 | md-links | No dual [url](url) links in the markdown | Dual link [url](url); prefer a bare URL (autolinked) or real anchor text: https://www.oasis-open.org/committees/openeox/ipr.php | Dual link [url](url); prefer a bare URL (autolinked) or real anchor text: https://www.oasis-open.org/policies-guidelines/trademark/ | text and target being the same URL calls for a bare autolink or real anchor text |
| 37 | PASS | md-links | No bare URL runs into '.\' without a space | links_scanned: 53 | the safe form '. \' (otherwise pandoc pulls the period and backslash into the href) |
| 38 | PASS | fence-collapse | No opening code fence carries trailing text in its info string | fences_scanned: 42 | a bare language token or curly-attribute form; trailing text collapses the block (lint D6) |
| 39 | PASS | image-policy | No empty img src attributes | img_tags: 1; image_payload_bytes: 0 | src must be non-empty |
| 40 | PASS | image-policy | No absolute-path image sources | img_tags: 1; image_payload_bytes: 0 | a leading / resolves outside the package on publication |
| 41 | PASS | image-policy | No path-traversal image sources | img_tags: 1; image_payload_bytes: 0 | the path must not contain .. segments |
| 42 | PASS | image-policy | No responsive srcset image constructs | img_tags: 1; image_payload_bytes: 0 | the publication pipeline's self-containment policy refuses srcset |
| 43 | PASS | image-policy | No <picture> elements | img_tags: 1; image_payload_bytes: 0 | the publication pipeline's self-containment policy refuses <picture> |
| 44 | PASS | image-policy | Every image file is under the per-image size cap | img_tags: 1; image_payload_bytes: 0 | the pipeline's 2MB per-image refusal cap |
| 45 | PASS | image-policy | No SVG carries script content | img_tags: 1; image_payload_bytes: 0 | <script> elements are active content, refused on docs.oasis-open.org |
| 46 | PASS | image-policy | No SVG carries inline event handlers | img_tags: 1; image_payload_bytes: 0 | on*= attributes are active content, refused |
| 47 | PASS | image-policy | No SVG references external image or use targets | img_tags: 1; image_payload_bytes: 0 | external <image>/<use> hrefs break self-containment |
| 48 | PASS | image-policy | Total image payload is under the cumulative cap | img_tags: 1; image_payload_bytes: 0 | the pipeline's 5MB cumulative inlining cap |
| 49 | PASS | pdf-cover | The document title appears exactly once on the PDF cover page | title: OpenEoX Core Schema Version 1.0; cover_page_occurrences: 1; runner_path_in_pdf: False | exactly 1 (more means stale title-block residue baked into the render, assertion A1) |
| 50 | PASS | pdf-cover | No CI runner path anywhere in the PDF text | title: OpenEoX Core Schema Version 1.0; cover_page_occurrences: 1; runner_path_in_pdf: False | the /home/runner/ path must not occur (assertion A2) |
| 51 | PASS | schema-id | Every .json file in the package parses as JSON | json_files: 2; expected_id_root: https://docs.oasis-open.org/openeox/eox-core/v1.0/ | must parse without error |
| 52 | PASS | schema-id | A flattened $id under the version root is a conscious convention | json_files: 2; expected_id_root: https://docs.oasis-open.org/openeox/eox-core/v1.0/ | the file's publish path; a version-root flattened $id (CSAF v2.0 style) needs a copy at that location |
| 53 | PASS | schema-id | Each schema's $id agrees with where the file publishes | json_files: 2; expected_id_root: https://docs.oasis-open.org/openeox/eox-core/v1.0/ | the canonical latest-version URL derived from the package path |
| 54 | PASS | schema-id | Schema-internal self-references agree with the declared $id | json_files: 2; expected_id_root: https://docs.oasis-open.org/openeox/eox-core/v1.0/ | the schema's own declared $id |
| 55 | PASS | pdf-sync | The PDF cross-check toolchain is available | pdftotext: present; this_stage_base_in_pdf: True | pdftotext present; absent means the PDF front-matter cross-check is skipped here and runs at intake |
| 56 | PASS | pdf-sync | pdftotext executes against the PDF | pdftotext: present; this_stage_base_in_pdf: True | a clean execution |
| 57 | PASS | pdf-sync | The PDF is machine-readable | pdftotext: present; this_stage_base_in_pdf: True | exit 0 |
| 58 | PASS | pdf-sync | The PDF front matter carries the canonical this-stage URL | pdftotext: present; this_stage_base_in_pdf: True | the this-stage base URL declared by the package front matter |
| 59 | PASS | pdf-sync | The PDF cites no unexpected other version of this spec | pdftotext: present; this_stage_base_in_pdf: True | the package's own version (previous-stage citations expected, anything else confirmed) |
| 60 | PASS | template | All required template front-matter sections are present | sections_found: Abstract, Chair(s), Citation format, Editor(s), Latest stage/version, Notices, Previous stage/version, Technical Committee, This stage/version; conformance_section: True | the template's required set: This/Previous/Latest stage, Technical Committee, Chairs, Editors, Abstract |
| 61 | PASS | template | Front-matter sections appear in template order | sections_found: Abstract, Chair(s), Citation format, Editor(s), Latest stage/version, Notices, Previous stage/version, Technical Committee, This stage/version; conformance_section: True | the canonical template ordering |
| 62 | PASS | template | A Conformance section exists | sections_found: Abstract, Chair(s), Citation format, Editor(s), Latest stage/version, Notices, Previous stage/version, Technical Committee, This stage/version; conformance_section: True | the TC Process requirement: every Standards Track Work Product carries conformance clauses |
| 63 | PASS | template-css | A non-canonical stylesheet keeps the template font family | stylesheet_links: 0; inline_style_blocks: 1 | the template look: Liberation Sans / Arial / Helvetica |
| 64 | PASS | template-css | The HTML carries a stylesheet | stylesheet_links: 0; inline_style_blocks: 1 | at least one styling source must be present |
| 65 | PASS | package-refs | Every file the document cites under its own stage path ships in the package | own_stage_citations_checked: 6 | the cited relative path must exist as a file in the package |
| 66 | PASS | link-mismatch | Visible URL text and its link target agree | shown_target_pairs: 3 | shown and target must be the same URL (a disagreement is a rename artifact) |
| 67 | PASS | double-slash | No relative link path contains a double slash | double_slash_paths: 0 | single slashes only (the CDN 404s a double slash even where browsers tolerate it) |
| 68 | WARN | cover-hr | No horizontal rule between the OASIS logo and the title | Horizontal rule between the OASIS logo and the title: the publication CSS treats <hr/> as a page break, which opens the PDF with a blank page. Harmless in other renderers; remove if publishing through the OASIS HTML-to-PDF path. | no --- / *** / ___ rule after the logo (the publication CSS renders it as a PDF page break) |
| 69 | PASS | pdf-fonts | pdffonts executes against the PDF | css_declared_families: couriernew, liberationsans; pdf_embedded_fonts: LibertinusSerif, NewCM10, NewCMMath | a clean execution |
| 70 | WARN | pdf-fonts | The PDF's embedded fonts are declared by the package's own CSS | PDF embeds fonts not declared by the package's own CSS: LibertinusSerif, NewCM10, NewCMMath. The CSS declares: couriernew, liberationsans. Confirm the divergence is intentional (pdffonts <file.pdf> re-checks this after a toolchain change). | the font families declared in the package's HTML/CSS (its own typography authority) |
| 71 | NA | manifest | manifest.json parses as JSON | NA: no manifest.json in the package (noted as informational) | must parse without error |
| 72 | NA | manifest | Every manifest item exists in the package | NA: no manifest.json in the package (noted as informational) | the package file tree |
| 73 | NA | manifest | Every manifest sha256 matches the file's actual digest | NA: no manifest.json in the package (noted as informational) | the digest recorded in the manifest |
| 74 | PASS | junk-files | No working directories inside the package | files_walked: 6 | forbidden set: __MACOSX, .git, .venv, venv, node_modules |
| 75 | PASS | junk-files | No OS junk or editor backup files in the package | files_walked: 6 | forbidden: .DS_Store, Thumbs.db, desktop.ini, and ~ / .bak / .orig / .swp suffixes |
| 76 | PASS | case | Every filename in the package is lowercase | md_docs_urls_scanned: 16; mixed_case_files: (none) | its lowercase form (the publication origin is case-sensitive; the canonical logo filename is exempt) |
| 77 | PASS | case | Every self-referential docs.oasis-open.org URL path is lowercase (markdown source) | md_docs_urls_scanned: 16; mixed_case_files: (none) | its lowercase form (case-sensitive origin; /templates/ paths exempt) |
| 78 | NA | case | Every self-referential docs.oasis-open.org URL path is lowercase (HTML render) | NA: evaluated on the markdown-source row for this package | its lowercase form (case-sensitive origin; /templates/ paths exempt) |
| 79 | PASS | symlinks | No symlink points at itself or an ancestor directory | symlinks_found: 0 | must not equal or contain its own directory (deploys materialize symlinks into unbounded recursion) |
| 80 | PASS | dead-lists | No reference to a lists.oasis-open.org mailing address (markdown source) | md_lists_addresses: (none) | the dead-infrastructure rule: that mail host silently fails; comments route via Higher Logic |
| 81 | NA | dead-lists | No reference to a lists.oasis-open.org mailing address (HTML render) | NA: evaluated on the markdown-source row for this package | the dead-infrastructure rule: that mail host silently fails; comments route via Higher Logic |
| 82 | PASS | dead-lists | Links into the retired list archives are flagged for verification | md_lists_addresses: (none) | each must be individually verified while the archive infrastructure is retired |
| 83 | PASS | rfc-keywords | Normative key words are backed by an RFC 2119 citation | normative_keywords_present: True; rfc2119_cited: True; rfc8174_cited: True | an RFC 2119 citation must be present when key words are used |
| 84 | PASS | rfc-keywords | RFC 2119 citation is paired with RFC 8174 | normative_keywords_present: True; rfc2119_cited: True; rfc8174_cited: True | the current template cites both 2119 and 8174 (uppercase-only clarification) |
| 85 | PASS | logo | The cover logo is the canonical OASIS logo | logo_sources: https://docs.oasis-open.org/templates/OASISLogo-v3.0.png | https://docs.oasis-open.org/templates/OASISLogo-v3.0.png |
| 86 | PASS | previous-stage | A stage past 01 cites its previous stage | pulled: the URLs in the markdown's Previous-stage block; no violating instance found | at least one docs.oasis-open.org URL required when the revision number exceeds 01 |
| 87 | NA | previous-stage | A stage past 01 cites its previous stage on the HTML cover | NA: DOCX-render condition; this package carries no Word source | at least one docs.oasis-open.org URL required when the revision number exceeds 01 |
| 88 | PASS | date-sync | The markdown front-matter date appears in the HTML | document_date: (not found); copyright_year: (not found) | the rendered HTML text (absence means the HTML came from a different revision) |
| 89 | PASS | date-sync | The copyright year matches the document date year | document_date: (not found); copyright_year: (not found) | the year of the front-matter document date |
| 90 | NA | generator | A DOCX-native render was produced by Microsoft Word | NA: DOCX-render condition; this package carries no Word source | must contain 'Microsoft Word' (a LibreOffice render differs in kind from the TC's precedent) |
| 91 | PASS | vml-fallback | Every VML image has an <![if !vml]> img fallback | vml_images: 0; img_fallbacks: 0 | fallback count must cover VML count (the invisible-cover-logo class) |
| 92 | PASS | asset-refs | Every relative src/href the HTML references ships in the package | relative_refs_checked: 0; missing: 0 | the package file tree; a missing target 404s on publication |
