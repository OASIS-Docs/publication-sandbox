<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# Policy authority for the OASIS publication acceptance criteria

**Author: Michael Coletta, Technical Advisor, OASIS Open**

This catalog records, for the acceptance-criteria checks that trace to written OASIS policy, exactly which policy each one answers to: the governing document, the section, and the verbatim clause.

It was produced by the July 2026 authority-mapping exercise, which ran against the check registry as it then stood, 96 individual conditions. Of those, 38 are grounded in written policy and appear below; the remaining 58 are operational quality rules with no single written clause behind them, and are listed in the crosswalk instead.

The checks added on 21 July 2026, which took the registry to its current size (see [CHECKS.md](CHECKS.md) for the live count), were themselves derived from written policy, and each carries its governing clause inline in the registry's `compares_to` field. Folding them into this catalog is outstanding work; until then, read this file as the authority record for the original 96 and `CHECKS.md` as the complete inventory.

Corpus snapshot 2026-07-21. Every quote below is a verbatim substring of the snapshotted source; document digests are in `corpus/MANIFEST.json`. The governing documents are the OASIS TC Process, the Committee Operations Process, the Naming Directives v1.7, and the TC Handbook.

The check name and signature match the tool's own catalog (`CHECKS.md`); the `AC-*` ids are the policy-derived acceptance criteria in `criteria.yaml`.

## case

### case: Mixed-case filename

Acceptance criteria: AC-NAMING-10, AC-NAMING-11

- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > A directory must not contain two or more names (filenames or directory names) that differ ONLY in case.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.2 Stage (BLOCKER)
  > A stage abbreviation (with a revision number) must be used in lower case as a discrete path component for document identifier, document URI, and in principal document filenames.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > [tc-shortname] is the official machine-readable identifier string used in the TC's (Kavi) group name and in the OASIS Library TC root URI, in lower case

### case: Mixed-case path in docs.oasis-open.org URL

Acceptance criteria: AC-NAMING-11

- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.2 Stage (BLOCKER)
  > A stage abbreviation (with a revision number) must be used in lower case as a discrete path component for document identifier, document URI, and in principal document filenames.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > [tc-shortname] is the official machine-readable identifier string used in the TC's (Kavi) group name and in the OASIS Library TC root URI, in lower case

## date-sync

### date-sync: Copyright year

Acceptance criteria: AC-FRONTMATTER-16

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File formats and document repository (Policy requirement) (BLOCKER)
  > All Work Products must use the OASIS file naming scheme and must include the OASIS copyright notice.
- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.1 General (BLOCKER)
  > All documents and other files produced by the TC, including Work Products at any level of approval, must use the OASIS file naming scheme and must include the OASIS copyright notice

## filenames

### filenames: Missing delivery format(s)

Acceptance criteria: AC-FORMATS-01

- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.2 File Formats (BLOCKER)
  > All approved versions of OASIS Deliverables must be published in (1) editable source, (2) HTML or XHTML, and (3) PDF formats.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File formats and document repository (BLOCKER)
  > Approved OASIS deliverables must be published in three formats: an editable source format, HTML or XHTML, and PDF, with one designated as the authoritative version.

### filenames: No authoritative source artifact

Acceptance criteria: AC-FORMATS-03, AC-FORMATS-02

- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.2 File Formats (BLOCKER)
  > Editable formats of all versions of TC documents must be delivered to the TC’s document repository.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File formats and document repository (BLOCKER)
  > Editable formats of all versions of TC documents must be delivered to the TC's document repository.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 9 Notes - TC document repository (BLOCKER)
  > This fulfills the TC Process requirement "Editable formats of all versions of TC documents must be delivered to the TC's document repository"
- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.2 File Formats (BLOCKER)
  > The TC must explicitly designate one of those formats as the authoritative document.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File formats and document repository (BLOCKER)
  > Approved OASIS deliverables must be published in three formats: an editable source format, HTML or XHTML, and PDF, with one designated as the authoritative version.

### filenames: No delivery items found

Acceptance criteria: AC-FORMATS-01

- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.2 File Formats (BLOCKER)
  > All approved versions of OASIS Deliverables must be published in (1) editable source, (2) HTML or XHTML, and (3) PDF formats.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File formats and document repository (BLOCKER)
  > Approved OASIS deliverables must be published in three formats: an editable source format, HTML or XHTML, and PDF, with one designated as the authoritative version.

### filenames: carries a working token

Acceptance criteria: AC-NAMING-14

- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > The standard filename pattern for single-part work products is: Naming Directives v1.7 [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > A filename identifying a specific published instance (stage) of a Work Product, used in a required cover page URI , must have the following structure unless it is a filename associated with a Multi-Part or Errata Work Product: [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[TC Handbook: CommitteeSpecs](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecs.html)**, Naming and URIs after approval (BLOCKER)
  > Once approved, the work product carries the stage abbreviation cs followed by a revision number: for example, myspec-v1.0-cs01.html .
- **[TC Handbook: PublicReviews](https://docs.oasis-open.org/TChandbook/Reference/PublicReviews.html)**, Naming during public review / Policy requirement (BLOCKER)
  > a CSD at revision 01 going through public review is filed and referenced as my-spec-v1.0-csd01 , not as my-spec-v1.0-csprd01

### filenames: do not share one basename

Acceptance criteria: AC-NAMING-14

- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > The standard filename pattern for single-part work products is: Naming Directives v1.7 [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > A filename identifying a specific published instance (stage) of a Work Product, used in a required cover page URI , must have the following structure unless it is a filename associated with a Multi-Part or Errata Work Product: [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[TC Handbook: CommitteeSpecs](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecs.html)**, Naming and URIs after approval (BLOCKER)
  > Once approved, the work product carries the stage abbreviation cs followed by a revision number: for example, myspec-v1.0-cs01.html .
- **[TC Handbook: PublicReviews](https://docs.oasis-open.org/TChandbook/Reference/PublicReviews.html)**, Naming during public review / Policy requirement (BLOCKER)
  > a CSD at revision 01 going through public review is filed and referenced as my-spec-v1.0-csd01 , not as my-spec-v1.0-csprd01

### filenames: does not end in '-

Acceptance criteria: AC-NAMING-05, AC-NAMING-14

- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > [stage-abbrev][revisionNumber] : one of the current stage abbreviations above, followed immediately by a two-digit revision number (e.g., csd01 , cs02 ). For os , omit the revision number entirely.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > [stage-abbrev] is a stage abbreviation in lower case characters ( e.g. : csd, cnd, cs, cn, os)
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > [revisionNumber] is a two-digit number as prescribed below
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.2 Stage (BLOCKER)
  > A stage abbreviation (with a revision number) must be used in lower case as a discrete path component for document identifier, document URI, and in principal document filenames.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.3 Revision (BLOCKER)
  > Textually, a revision is a two-digit number associated with a specific stage corresponding to a published instance. A revision number begins with "01" and is incremented by 1 for each release at each maturity level (stage).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.3 Revision (BLOCKER)
  > A revision number is a required component within stage-specific filenames used on a document cover page .
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > The standard filename pattern for single-part work products is: Naming Directives v1.7 [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > A filename identifying a specific published instance (stage) of a Work Product, used in a required cover page URI , must have the following structure unless it is a filename associated with a Multi-Part or Errata Work Product: [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[TC Handbook: CommitteeSpecs](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecs.html)**, Naming and URIs after approval (BLOCKER)
  > Once approved, the work product carries the stage abbreviation cs followed by a revision number: for example, myspec-v1.0-cs01.html .
- **[TC Handbook: PublicReviews](https://docs.oasis-open.org/TChandbook/Reference/PublicReviews.html)**, Naming during public review / Policy requirement (BLOCKER)
  > a CSD at revision 01 going through public review is filed and referenced as my-spec-v1.0-csd01 , not as my-spec-v1.0-csprd01

## front-matter

### front-matter: 'Latest'-labelled URL carries the stage segment

Acceptance criteria: AC-FRONTMATTER-04

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Latest stage) (BLOCKER)
  > This is the only URI that may be updated (overwritten) when a newer version is published.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Latest stage : an alias URI that always points to the most current publication of this work product, regardless of stage or revision. Unlike the "This stage" URI, the latest-stage alias is overwritten with each new publication (it is the only URI that may be updated after a document is published).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > This locator URI does not contain the path component [stage-abbrev][revisionNumber] or stage identifier in the filename.

### front-matter: Latest-stage URL must point at the version root

Acceptance criteria: AC-FRONTMATTER-04

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Latest stage) (BLOCKER)
  > This is the only URI that may be updated (overwritten) when a newer version is published.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Latest stage : an alias URI that always points to the most current publication of this work product, regardless of stage or revision. Unlike the "This stage" URI, the latest-stage alias is overwritten with each new publication (it is the only URI that may be updated after a document is published).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > This locator URI does not contain the path component [stage-abbrev][revisionNumber] or stage identifier in the filename.

### front-matter: Latest-stage URL not under

Acceptance criteria: AC-FRONTMATTER-04

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Latest stage) (BLOCKER)
  > This is the only URI that may be updated (overwritten) when a newer version is published.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Latest stage : an alias URI that always points to the most current publication of this work product, regardless of stage or revision. Unlike the "This stage" URI, the latest-stage alias is overwritten with each new publication (it is the only URI that may be updated after a document is published).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > This locator URI does not contain the path component [stage-abbrev][revisionNumber] or stage identifier in the filename.

### front-matter: Latest-version URL must point at the version root

Acceptance criteria: AC-FRONTMATTER-04

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Latest stage) (BLOCKER)
  > This is the only URI that may be updated (overwritten) when a newer version is published.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Latest stage : an alias URI that always points to the most current publication of this work product, regardless of stage or revision. Unlike the "This stage" URI, the latest-stage alias is overwritten with each new publication (it is the only URI that may be updated after a document is published).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > This locator URI does not contain the path component [stage-abbrev][revisionNumber] or stage identifier in the filename.

### front-matter: No 'This stage' URL block

Acceptance criteria: AC-FRONTMATTER-01

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (BLOCKER)
  > Every Work Product must display its persistent URIs on the cover page. OASIS Naming Directives v1.7 requires exactly three URI fields, each serving a distinct and permanent role.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Policy requirement) (BLOCKER)
  > All three URI fields must appear on the cover page. Published resources in the OASIS Library must not be deleted or altered; only the "latest stage" alias may be overwritten.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Every published work product must carry exactly three version URIs on its cover page.
- **[TC Handbook: CommitteeNoteDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeNoteDrafts.html)**, CND filename and URI pattern examples (BLOCKER)
  > Every published CND cover page must carry three required URIs: This stage , Previous stage , and Latest stage .
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > OASIS requires that Work Products present three general kinds of URIs as display metadata, illustrated below: This stage , Previous stage (when applicable), and Latest stage .

### front-matter: No 'This version' URL block found on the HTML cover

Acceptance criteria: AC-FRONTMATTER-01

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (BLOCKER)
  > Every Work Product must display its persistent URIs on the cover page. OASIS Naming Directives v1.7 requires exactly three URI fields, each serving a distinct and permanent role.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Policy requirement) (BLOCKER)
  > All three URI fields must appear on the cover page. Published resources in the OASIS Library must not be deleted or altered; only the "latest stage" alias may be overwritten.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Every published work product must carry exactly three version URIs on its cover page.
- **[TC Handbook: CommitteeNoteDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeNoteDrafts.html)**, CND filename and URI pattern examples (BLOCKER)
  > Every published CND cover page must carry three required URIs: This stage , Previous stage , and Latest stage .
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > OASIS requires that Work Products present three general kinds of URIs as display metadata, illustrated below: This stage , Previous stage (when applicable), and Latest stage .

### front-matter: Stage URL is not under

Acceptance criteria: AC-NAMING-24, AC-PACKAGING-19

- **[TC Handbook: CommitteeSpecDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecDrafts.html)**, Submitting a CSD for publication (BLOCKER)
  > Staff publish the CSD to the OASIS Library at a URI following the pattern: https://docs.oasis-open.org/[tc-shortname]/[WP-abbrev]/[version]/csd[NN]/
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, URI pattern (BLOCKER)
  > Published documents are assigned permanent URIs under docs.oasis-open.org . The pattern is: Naming Directives v1.7 https://docs.oasis-open.org/[tc-shortname]/[WP-abbrev]/[version-id]/[stage-abbrev][revisionNumber]/[doc-id].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > URIs serving as primary identifiers (Document URIs) for Work Products installed in the OASIS Library must conform to this pattern unless they are URI references associated with a Multi-Part or Approved Errata Work Product: https://docs.oasis-open.org/ [tc-shortname]/[WP-abbrev]/[version-id]/[stage-abbrev][revisionNumber]/[doc-id].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > [tc-shortname] is the official machine-readable identifier string used in the TC's (Kavi) group name and in the OASIS Library TC root URI, in lower case
- **[OASIS Committee Operations Process](https://www.oasis-open.org/policies-guidelines/oasis-committee-operations-process/)**, 1.5 Committee Visibility and Transparency (BLOCKER)
  > All web pages, documents, ballot results and email archives of all committees and subcommittees shall be publicly visible.
- **[OASIS Committee Operations Process](https://www.oasis-open.org/policies-guidelines/oasis-committee-operations-process/)**, 1.5 Committee Visibility and Transparency (BLOCKER)
  > The official copies of all resources of a committee and any associated subcommittees, including web pages, documents, email lists and any other records of discussions, must be located only on facilities designated by OASIS.
- **[OASIS Committee Operations Process](https://www.oasis-open.org/policies-guidelines/oasis-committee-operations-process/)**, 1.5 Committee Visibility and Transparency (BLOCKER)
  > Committees may not conduct official business or technical discussions, store documents, or host web pages on servers or systems not designated by OASIS.

### front-matter: This-stage URL does not contain

Acceptance criteria: AC-NAMING-24

- **[TC Handbook: CommitteeSpecDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecDrafts.html)**, Submitting a CSD for publication (BLOCKER)
  > Staff publish the CSD to the OASIS Library at a URI following the pattern: https://docs.oasis-open.org/[tc-shortname]/[WP-abbrev]/[version]/csd[NN]/
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, URI pattern (BLOCKER)
  > Published documents are assigned permanent URIs under docs.oasis-open.org . The pattern is: Naming Directives v1.7 https://docs.oasis-open.org/[tc-shortname]/[WP-abbrev]/[version-id]/[stage-abbrev][revisionNumber]/[doc-id].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > URIs serving as primary identifiers (Document URIs) for Work Products installed in the OASIS Library must conform to this pattern unless they are URI references associated with a Multi-Part or Approved Errata Work Product: https://docs.oasis-open.org/ [tc-shortname]/[WP-abbrev]/[version-id]/[stage-abbrev][revisionNumber]/[doc-id].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > [tc-shortname] is the official machine-readable identifier string used in the TC's (Kavi) group name and in the OASIS Library TC root URI, in lower case

### front-matter: This-stage block does not list

Acceptance criteria: AC-FORMATS-01, AC-FRONTMATTER-01

- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.2 File Formats (BLOCKER)
  > All approved versions of OASIS Deliverables must be published in (1) editable source, (2) HTML or XHTML, and (3) PDF formats.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File formats and document repository (BLOCKER)
  > Approved OASIS deliverables must be published in three formats: an editable source format, HTML or XHTML, and PDF, with one designated as the authoritative version.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (BLOCKER)
  > Every Work Product must display its persistent URIs on the cover page. OASIS Naming Directives v1.7 requires exactly three URI fields, each serving a distinct and permanent role.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Policy requirement) (BLOCKER)
  > All three URI fields must appear on the cover page. Published resources in the OASIS Library must not be deleted or altered; only the "latest stage" alias may be overwritten.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Every published work product must carry exactly three version URIs on its cover page.
- **[TC Handbook: CommitteeNoteDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeNoteDrafts.html)**, CND filename and URI pattern examples (BLOCKER)
  > Every published CND cover page must carry three required URIs: This stage , Previous stage , and Latest stage .
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > OASIS requires that Work Products present three general kinds of URIs as display metadata, illustrated below: This stage , Previous stage (when applicable), and Latest stage .

### front-matter: This-version URL does not contain

Acceptance criteria: AC-NAMING-24

- **[TC Handbook: CommitteeSpecDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecDrafts.html)**, Submitting a CSD for publication (BLOCKER)
  > Staff publish the CSD to the OASIS Library at a URI following the pattern: https://docs.oasis-open.org/[tc-shortname]/[WP-abbrev]/[version]/csd[NN]/
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, URI pattern (BLOCKER)
  > Published documents are assigned permanent URIs under docs.oasis-open.org . The pattern is: Naming Directives v1.7 https://docs.oasis-open.org/[tc-shortname]/[WP-abbrev]/[version-id]/[stage-abbrev][revisionNumber]/[doc-id].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > URIs serving as primary identifiers (Document URIs) for Work Products installed in the OASIS Library must conform to this pattern unless they are URI references associated with a Multi-Part or Approved Errata Work Product: https://docs.oasis-open.org/ [tc-shortname]/[WP-abbrev]/[version-id]/[stage-abbrev][revisionNumber]/[doc-id].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.1 Path Components in Document URIs (BLOCKER)
  > [tc-shortname] is the official machine-readable identifier string used in the TC's (Kavi) group name and in the OASIS Library TC root URI, in lower case

### front-matter: which is not a file in the package

Acceptance criteria: AC-FRONTMATTER-02

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (This stage) (BLOCKER)
  > The exact published artifact at this version and stage (e.g., …/csd01/… ). Unique; never reused for a different document.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > A URI specific to the Work Product current at the time of publication; it is persistent, permanently assigned to one particular specification instance, and is never re-used.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.4 URI Persistence (BLOCKER)
  > URIs for published OASIS resources must be persistent.

## html-anchors

### html-anchors: has no matching anchor in the HTML

Acceptance criteria: AC-CONTENT-06

- **[TC Handbook: WPQualityChecklist](https://docs.oasis-open.org/TChandbook/Reference/WPQualityChecklist.html)**, Editorial quality verification checklist, key areas (WARN)
  > Document consistency: section numbers, cross-references, defined term capitalization, and table of contents are current and internally consistent.

### html-anchors: no internal (fragment) links at all

Acceptance criteria: AC-CONTENT-06

- **[TC Handbook: WPQualityChecklist](https://docs.oasis-open.org/TChandbook/Reference/WPQualityChecklist.html)**, Editorial quality verification checklist, key areas (WARN)
  > Document consistency: section numbers, cross-references, defined term capitalization, and table of contents are current and internally consistent.

## junk-files

### junk-files: Junk file in package

Acceptance criteria: AC-NAMING-09, AC-NAMING-13

- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > Filenames and directory names must neither begin nor end with a punctuation character (period or hyphen).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > Filenames and directory names must not contain multiple (2+) consecutive punctuation characters
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Allowed characters (Policy requirement) (BLOCKER)
  > No leading, trailing, or consecutive punctuation characters are allowed.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > filenames having special meaning for operating systems or for OASIS server software must not be used in any Work Product. For example, the following are forbidden: index.html , index.htm , *.cgi, and .htaccess.

## pdf-sync

### pdf-sync: does not contain the canonical this-stage base URL

Acceptance criteria: AC-FRONTMATTER-01

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (BLOCKER)
  > Every Work Product must display its persistent URIs on the cover page. OASIS Naming Directives v1.7 requires exactly three URI fields, each serving a distinct and permanent role.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Policy requirement) (BLOCKER)
  > All three URI fields must appear on the cover page. Published resources in the OASIS Library must not be deleted or altered; only the "latest stage" alias may be overwritten.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Every published work product must carry exactly three version URIs on its cover page.
- **[TC Handbook: CommitteeNoteDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeNoteDrafts.html)**, CND filename and URI pattern examples (BLOCKER)
  > Every published CND cover page must carry three required URIs: This stage , Previous stage , and Latest stage .
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > OASIS requires that Work Products present three general kinds of URIs as display metadata, illustrated below: This stage , Previous stage (when applicable), and Latest stage .

## previous-stage

### previous-stage: no Previous-version block with docs.oasis-open.org URLs found on the HTML cover

Acceptance criteria: AC-FRONTMATTER-03

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Previous stage) (BLOCKER)
  > The immediately preceding published instance of this Work Product (e.g., prior CSD revision or CS). Write "N/A" if this is the first published version.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > If the current publication is the very first instance, the text "N/A" is used.

### previous-stage: the Previous-Stage block is empty or N/A

Acceptance criteria: AC-FRONTMATTER-03

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Previous stage) (BLOCKER)
  > The immediately preceding published instance of this Work Product (e.g., prior CSD revision or CS). Write "N/A" if this is the first published version.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > If the current publication is the very first instance, the text "N/A" is used.

## revision-collision

### revision-collision: is already published at

Acceptance criteria: AC-FRONTMATTER-02, AC-PACKAGING-16, AC-NAMING-30

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (This stage) (BLOCKER)
  > The exact published artifact at this version and stage (e.g., …/csd01/… ). Unique; never reused for a different document.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > A URI specific to the Work Product current at the time of publication; it is persistent, permanently assigned to one particular specification instance, and is never re-used.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.4 URI Persistence (BLOCKER)
  > URIs for published OASIS resources must be persistent.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.3 Resource Permanence (BLOCKER)
  > resources published in the OASIS Library , TC Document Repository , and other venues must not be deleted or otherwise altered. Resources may be revised, but all revisions are retained.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.3 Resource Permanence (BLOCKER)
  > content instantiated as regular files and directories must not be over-written, replaced, renamed, or removed.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Latest stage) (BLOCKER)
  > This is the only URI that may be updated (overwritten) when a newer version is published.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Latest stage : an alias URI that always points to the most current publication of this work product, regardless of stage or revision. Unlike the "This stage" URI, the latest-stage alias is overwritten with each new publication (it is the only URI that may be updated after a document is published).
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Persistence (Policy requirement) (BLOCKER)
  > Published resources in the OASIS Library must not be deleted or altered after publication. The only exception is the "Latest stage" alias URI, which is designed to be overwritten each time a newer stage is published. All other published URIs, "This stage" and "Previous stage", are permanent and immutable once assigned.
- **[TC Handbook: WorkProductLifecycle](https://docs.oasis-open.org/TChandbook/Reference/WorkProductLifecycle.html)**, Common misconception (lifecycle overview) (BLOCKER)
  > Once a TC approves its first Committee Specification Draft (and, later, after CS01 is approved), the work product does not return to the Working Draft stage.
- **[TC Handbook: WorkingDrafts](https://docs.oasis-open.org/TChandbook/Reference/WorkingDrafts.html)**, Common misconception (BLOCKER)
  > The TC Process defines no mechanism to return an approved CSD or CS to Working Draft.
- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.4 Work Product Approvals (BLOCKER)
  > Each of the progressions above must begin with step 1, and no step may be skipped.
- **[TC Handbook: Glossary](https://docs.oasis-open.org/TChandbook/Concepts/Glossary.html)**, Working Draft (WD) (BLOCKER)
  > Once a document has been approved as a Work Product it does not revert to Working Draft status.

## rfc-keywords

### rfc-keywords: RFC 8174

Acceptance criteria: AC-CONTENT-07

- **[TC Handbook: WPQualityChecklist](https://docs.oasis-open.org/TChandbook/Reference/WPQualityChecklist.html)**, Editorial quality verification checklist, key areas (WARN)
  > Keyword guidelines: RFC 2119 / BCP 14 keywords (MUST, SHALL, SHOULD, MAY, etc.) used consistently and declared in a keywords section where employed.
- **[TC Handbook: Conformance](https://docs.oasis-open.org/TChandbook/Reference/Conformance.html)**, Normative versus non-normative content (WARN)
  > When a specification incorporates RFC 2119 (or its successor BCP 14) for normative keywords, the Guidelines recommend stating that in the conformance section or in the introductory section on conventions.

### rfc-keywords: does not cite RFC 2119

Acceptance criteria: AC-CONTENT-07

- **[TC Handbook: WPQualityChecklist](https://docs.oasis-open.org/TChandbook/Reference/WPQualityChecklist.html)**, Editorial quality verification checklist, key areas (WARN)
  > Keyword guidelines: RFC 2119 / BCP 14 keywords (MUST, SHALL, SHOULD, MAY, etc.) used consistently and declared in a keywords section where employed.
- **[TC Handbook: Conformance](https://docs.oasis-open.org/TChandbook/Reference/Conformance.html)**, Normative versus non-normative content (WARN)
  > When a specification incorporates RFC 2119 (or its successor BCP 14) for normative keywords, the Guidelines recommend stating that in the conformance section or in the introductory section on conventions.

## schema-id

### schema-id: not valid JSON (

Acceptance criteria: AC-FORMATS-04

- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.5 Computer Language Definitions (BLOCKER)
  > All normative computer language definitions must also be provided in separate plain text files;
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Machine-readable definitions (Standards Track, mandatory) (BLOCKER)
  > This requirement applies to any machine-readable artifact that carries normative weight: embedding schema content only within a document body, without a standalone plain-text file, does not satisfy §2.2.5. Non-Standards Track Work Products are not subject to this requirement.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Machine-readable definitions (Standards Track, mandatory) (Policy requirement) (BLOCKER)
  > All normative computer language definitions in a Standards Track Work Product must be well-formed and valid, and must also be provided in separate plain-text files . The specification must clearly reference those separate files.
- **[TC Handbook: WPQualityChecklist](https://docs.oasis-open.org/TChandbook/Reference/WPQualityChecklist.html)**, Editorial quality verification checklist, key areas (BLOCKER)
  > Machine-readable definitions (Standards Track): any machine-readable content (schemas, grammars, code) must be provided as separate plain-text files alongside the specification document.
- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.5 Computer Language Definitions (BLOCKER)
  > All normative computer language definitions that are part of the Work Product, such as XML instances, schemas or Java(TM) code, including fragments of such, must be well formed and valid.

## stage-name

### stage-name: is missing its two-digit number

Acceptance criteria: AC-NAMING-05, AC-NAMING-04

- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > [stage-abbrev][revisionNumber] : one of the current stage abbreviations above, followed immediately by a two-digit revision number (e.g., csd01 , cs02 ). For os , omit the revision number entirely.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > [stage-abbrev] is a stage abbreviation in lower case characters ( e.g. : csd, cnd, cs, cn, os)
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > [revisionNumber] is a two-digit number as prescribed below
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.2 Stage (BLOCKER)
  > A stage abbreviation (with a revision number) must be used in lower case as a discrete path component for document identifier, document URI, and in principal document filenames.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.3 Revision (BLOCKER)
  > Textually, a revision is a two-digit number associated with a specific stage corresponding to a published instance. A revision number begins with "01" and is incremented by 1 for each release at each maturity level (stage).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.3 Revision (BLOCKER)
  > A revision number is a required component within stage-specific filenames used on a document cover page .
- **[TC Handbook: WorkProductLifecycle](https://docs.oasis-open.org/TChandbook/Reference/WorkProductLifecycle.html)**, Standards Track (OASIS Standard) (BLOCKER)
  > The os stage abbreviation never carries a revision number.
- **[TC Handbook: OASISStandard](https://docs.oasis-open.org/TChandbook/Reference/OASISStandard.html)**, After approval (BLOCKER)
  > The published OASIS Standard uses the os stage abbreviation, which never carries a revision number.
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.2 Stage (BLOCKER)
  > The os stage abbreviation is never used with a revision number.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Current stage abbreviations (table: os) (BLOCKER)
  > Never carries a revision number. Only one OASIS Standard per version.
- **[TC Handbook: Glossary](https://docs.oasis-open.org/TChandbook/Concepts/Glossary.html)**, OASIS Standard (BLOCKER)
  > The stage abbreviation is os , which never carries a revision number.

### stage-name: is not a recognized stage token

Acceptance criteria: AC-NAMING-02, AC-NAMING-03

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File naming and URI pattern (BLOCKER)
  > Standards Track: csd , cs , os , errata (the os stage never carries a revision number).
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.2 Stage (BLOCKER)
  > a release is thus identified using a string matching "[stage-abbrev][revisionNumber]", where "stage-abbrev" is one of the following, in lower case: csd, cs, os, errata, cnd, cn.
- **[TC Handbook: Maintenance](https://docs.oasis-open.org/TChandbook/Reference/Maintenance.html)**, Naming and stage abbreviation (BLOCKER)
  > Documents published through the Approved Errata process use the errata stage abbreviation in their filenames and URIs. This is one of the four current Standards Track stage abbreviations: csd , cs , os , errata .
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File naming and URI pattern (BLOCKER)
  > Current stage abbreviations for the two tracks are: Standards Track: csd , cs , os , errata (the os stage never carries a revision number). Non-Standards Track: cnd , cn .
- **[TC Handbook: Glossary](https://docs.oasis-open.org/TChandbook/Concepts/Glossary.html)**, Committee Note (CN) (BLOCKER)
  > The stage abbreviations are cnd (draft) and cn (approved). The former stage designation cnprd was removed in Naming Directives v1.7 (effective 2 January 2024) and must not be used.
- **[TC Handbook: CommitteeNotes](https://docs.oasis-open.org/TChandbook/Reference/CommitteeNotes.html)**, Stage abbreviations and naming (BLOCKER)
  > Current valid stage abbreviations for Non-Standards Track documents are cnd (Committee Note Draft) and cn (Committee Note). The abbreviation cnprd was removed in Naming Directives v1.7 . Do not use cnprd in filenames or URIs.

### stage-name: uses a retired/invalid stage token

Acceptance criteria: AC-NAMING-01

- **[TC Handbook: PublicReviews](https://docs.oasis-open.org/TChandbook/Reference/PublicReviews.html)**, What changed since the 2010 handbook / Stage names removed (BLOCKER)
  > Do not use csprd or cnprd in any filename, URI, or cover page.
- **[TC Handbook: CommitteeSpecs](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecs.html)**, Naming and URIs after approval (BLOCKER)
  > The abbreviation csprd is obsolete and must not be used .
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File naming and URI pattern (BLOCKER)
  > The abbreviations csprd , cnprd , and cos are obsolete and removed as of Naming Directives v1.7.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Historical note (BLOCKER)
  > The following abbreviations were used before Naming Directives v1.7 (January 2, 2024) and are now obsolete and removed : csprd (Committee Specification Public Review Draft), cnprd (Committee Note Public Review Draft), cos (Candidate OASIS Standard as a named stage). They must not appear in any new or revised work-product filenames or URIs.
- **[TC Handbook: CommitteeNoteDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeNoteDrafts.html)**, Naming and URI conventions (BLOCKER)
  > The abbreviations cnprd and csprd were removed from the Naming Directives in v1.7 (effective 2 January 2024) and must not appear in new filenames or URIs.

## template

### template: No Conformance section found

Acceptance criteria: AC-CONTENT-01

- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.6 Conformance Clauses (BLOCKER)
  > A Standards Track Work Product that is approved by the TC at the Committee Specification Public Review Draft, Committee Specification or OASIS Standard level must include a separate section, listing a set of numbered conformance clauses , to which any implementation of the specification must adhere in order to claim conformance to the specification (or any optional portion thereof).
- **[TC Handbook: Conformance](https://docs.oasis-open.org/TChandbook/Reference/Conformance.html)**, When conformance clauses are required (Policy requirement) (BLOCKER)
  > A Standards Track work product must include a conformance clause section before it can be submitted for public review (the Committee Specification Public Review Draft stage), approved as a Committee Specification (CS) , or approved as an OASIS Standard (OS) .
- **[TC Handbook: WorkProductLifecycle](https://docs.oasis-open.org/TChandbook/Reference/WorkProductLifecycle.html)**, Standards Track (Public Review) (BLOCKER)
  > A Standards Track work product approved at the Committee Specification Public Review Draft , Committee Specification, or OASIS Standard level must include a separate, numbered conformance clause section
- **[TC Handbook: CommitteeSpecDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecDrafts.html)**, Quality requirements at the csd stage (BLOCKER)
  > The trigger is therefore the public-review stage (the Committee Specification Public Review Draft level), not the initial §2.5 CSD-approval ballot . A CSD approved only for internal development need not yet carry the conformance section; the obligation attaches when that CSD is submitted for public review.
- **[TC Handbook: Conformance](https://docs.oasis-open.org/TChandbook/Reference/Conformance.html)**, Required structure of the conformance section (BLOCKER)
  > Work product templates provided by OASIS TC Administration include a placeholder conformance section; editors must populate it with substantive clauses before the work product is submitted for public review.

### template: Required front-matter section missing

Acceptance criteria: AC-FRONTMATTER-01, AC-FRONTMATTER-08, AC-FRONTMATTER-16

- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (BLOCKER)
  > Every Work Product must display its persistent URIs on the cover page. OASIS Naming Directives v1.7 requires exactly three URI fields, each serving a distinct and permanent role.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (Policy requirement) (BLOCKER)
  > All three URI fields must appear on the cover page. Published resources in the OASIS Library must not be deleted or altered; only the "latest stage" alias may be overwritten.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Three required cover-page URIs (Policy requirement) (BLOCKER)
  > Every published work product must carry exactly three version URIs on its cover page.
- **[TC Handbook: CommitteeNoteDrafts](https://docs.oasis-open.org/TChandbook/Reference/CommitteeNoteDrafts.html)**, CND filename and URI pattern examples (BLOCKER)
  > Every published CND cover page must carry three required URIs: This stage , Previous stage , and Latest stage .
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 6.2 Required Document URIs (BLOCKER)
  > OASIS requires that Work Products present three general kinds of URIs as display metadata, illustrated below: This stage , Previous stage (when applicable), and Latest stage .
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, Cover-page metadata and the three required URIs (BLOCKER)
  > In addition to the URIs, every Work Product cover page must clearly state whether it is a Standards Track Work Product or Non-Standards Track Work Product . This designation is required regardless of stage.
- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.7 Notifications (BLOCKER)
  > Every Work Product must clearly indicate on the cover page whether it is a Standards Track Work Product or Non-Standards Track Work Product.
- **[TC Handbook: WPQualityRequirements](https://docs.oasis-open.org/TChandbook/Reference/WPQualityRequirements.html)**, File formats and document repository (Policy requirement) (BLOCKER)
  > All Work Products must use the OASIS file naming scheme and must include the OASIS copyright notice.
- **[OASIS TC Process (2017-05-26)](https://www.oasis-open.org/policies-guidelines/tc-process-2017-05-26/)**, 2.2.1 General (BLOCKER)
  > All documents and other files produced by the TC, including Work Products at any level of approval, must use the OASIS file naming scheme and must include the OASIS copyright notice

## version-naming

### version-naming: does not embed the version segment

Acceptance criteria: AC-NAMING-06, AC-NAMING-14

- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > [version-id] is a versioning identifier component composed of the single character "v" (lower case), followed by a numeric string matching the rules for Version
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.1 Version (BLOCKER)
  > A Version in this formal sense must be represented textually by a numeric string composed of digits [0-9] and period (".") corresponding to any of the approved lexical models
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > [version-id] : the version identifier in #.# , #.## , #.#.# , or ##.# form (e.g., v1.0 , v1.01 , v1.2.1 , v10.1 ). The version identifier should also appear in the work product's title.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > The standard filename pattern for single-part work products is: Naming Directives v1.7 [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > A filename identifying a specific published instance (stage) of a Work Product, used in a required cover page URI , must have the following structure unless it is a filename associated with a Multi-Part or Errata Work Product: [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[TC Handbook: CommitteeSpecs](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecs.html)**, Naming and URIs after approval (BLOCKER)
  > Once approved, the work product carries the stage abbreviation cs followed by a revision number: for example, myspec-v1.0-cs01.html .
- **[TC Handbook: PublicReviews](https://docs.oasis-open.org/TChandbook/Reference/PublicReviews.html)**, Naming during public review / Policy requirement (BLOCKER)
  > a CSD at revision 01 going through public review is filed and referenced as my-spec-v1.0-csd01 , not as my-spec-v1.0-csprd01

### version-naming: does not match the vN.N convention

Acceptance criteria: AC-NAMING-06

- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > [version-id] is a versioning identifier component composed of the single character "v" (lower case), followed by a numeric string matching the rules for Version
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.1 Version (BLOCKER)
  > A Version in this formal sense must be represented textually by a numeric string composed of digits [0-9] and period (".") corresponding to any of the approved lexical models
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > [version-id] : the version identifier in #.# , #.## , #.#.# , or ##.# form (e.g., v1.0 , v1.01 , v1.2.1 , v10.1 ). The version identifier should also appear in the work product's title.

### version-naming: the files were renamed

Acceptance criteria: AC-NAMING-06, AC-NAMING-14

- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > [version-id] is a versioning identifier component composed of the single character "v" (lower case), followed by a numeric string matching the rules for Version
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 5.1 Version (BLOCKER)
  > A Version in this formal sense must be represented textually by a numeric string composed of digits [0-9] and period (".") corresponding to any of the approved lexical models
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > [version-id] : the version identifier in #.# , #.## , #.#.# , or ##.# form (e.g., v1.0 , v1.01 , v1.2.1 , v10.1 ). The version identifier should also appear in the work product's title.
- **[TC Handbook: Naming](https://docs.oasis-open.org/TChandbook/Reference/Naming.html)**, Filename pattern (BLOCKER)
  > The standard filename pattern for single-part work products is: Naming Directives v1.7 [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[OASIS Naming Directives v1.7 (2 Jan 2024)](https://docs.oasis-open.org/specGuidelines/ndr/namingDirectives.html)**, 4 Name Construction Rules for Files and Directories (BLOCKER)
  > A filename identifying a specific published instance (stage) of a Work Product, used in a required cover page URI , must have the following structure unless it is a filename associated with a Multi-Part or Errata Work Product: [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber].[ext]
- **[TC Handbook: CommitteeSpecs](https://docs.oasis-open.org/TChandbook/Reference/CommitteeSpecs.html)**, Naming and URIs after approval (BLOCKER)
  > Once approved, the work product carries the stage abbreviation cs followed by a revision number: for example, myspec-v1.0-cs01.html .
- **[TC Handbook: PublicReviews](https://docs.oasis-open.org/TChandbook/Reference/PublicReviews.html)**, Naming during public review / Policy requirement (BLOCKER)
  > a CSD at revision 01 going through public review is filed and referenced as my-spec-v1.0-csd01 , not as my-spec-v1.0-csprd01
