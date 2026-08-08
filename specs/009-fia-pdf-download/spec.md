# Feature Specification: FIA Regulation PDF Downloader

**Feature Branch**: `009-fia-pdf-download`

**Created**: 2026-08-08

**Status**: Draft

**Input**: User description: "Build a script that downloads FIA regulation PDFs from https://api.fia.com/regulation/category/110 (a paginated Drupal listing, ?page=N, 0-indexed) and saves each PDF's metadata alongside it: title, source URL, the section/regulation this document belongs to (as stated in its title — no department mapping or categorization beyond that), issue/revision number, publish date, and the timestamp the script downloaded it. Download every issue found for a section, including superseded ones, not just the latest — this is a historical archive, not just \"current regulations.\" The script should be re-runnable without re-downloading files it already has (skip PDFs whose source URL was already downloaded). Respect the site's crawl-delay of 10 seconds between requests. Out of scope: parsing, chunking, embedding, or otherwise feeding the downloaded PDFs into the existing ingestion pipeline — this script's only job is fetch-and-save; ingestion remains a separate, already-existing step run manually afterward. Out of scope: department/category assignment — that stays a decision for ingestion time, not download time. Out of scope: scheduling or automatically re-running this on a timer."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build a local archive of regulation documents (Priority: P1)

A team member responsible for keeping the knowledge base current runs the downloader against a regulation category on the official site. The tool walks the full listing (however many pages it spans), downloads every regulation PDF it finds, and saves each one locally alongside a metadata record describing it — so there's a complete, ready-to-ingest local archive without anyone manually right-clicking "Save As" on dozens of individual documents.

**Why this priority**: This is the entire point of the feature — without it, there's no archive and nothing else matters. It's also independently useful on day one: even a single successful full run already replaces what would otherwise be manual, error-prone downloading.

**Independent Test**: Run the tool against the category URL with an empty local archive. Confirm every regulation document listed on the source site (across all its pages) ends up saved locally, each with a metadata record containing its title, source link, section/regulation, issue/revision, publish date, and the time it was downloaded.

**Acceptance Scenarios**:

1. **Given** an empty local archive, **When** the tool is run against the category, **Then** every regulation document listed across all pages of that category is downloaded and saved locally.
2. **Given** a document has just been downloaded, **When** its metadata record is inspected, **Then** it includes the document's title, source URL, section/regulation (as stated on the source page), issue/revision number, publish date, and the timestamp it was downloaded.
3. **Given** a section has multiple historical issues listed (e.g. issue 4 through issue 8 of the same regulation), **When** the tool runs, **Then** every issue is downloaded and saved as a separate document, not just the most recent one.

---

### User Story 2 - Re-run safely without redoing finished work (Priority: P2)

The same team member runs the downloader again later — maybe the site published new documents, maybe they just want to double-check nothing's missing. The tool skips everything it already has and only fetches what's new, so re-running is cheap, fast, and doesn't hammer the source site with redundant requests.

**Why this priority**: Without this, every re-run re-downloads the entire archive from scratch, which wastes time, wastes bandwidth, and is unnecessarily hard on the source site. It builds directly on User Story 1 and has no value on its own without it.

**Independent Test**: With a local archive already populated by a prior full run, run the tool again with no changes on the source site. Confirm zero documents are re-downloaded and the existing local archive is left untouched.

**Acceptance Scenarios**:

1. **Given** a document was already downloaded in a prior run, **When** the tool is run again, **Then** that document is not re-downloaded.
2. **Given** the source site has published a document that wasn't present in a prior run, **When** the tool is run again, **Then** only that new document is downloaded, and everything previously downloaded is left as-is.

---

### Edge Cases

- What happens when the source site is unreachable partway through a run? Documents already downloaded and saved before the failure remain intact; the run can simply be retried later and will pick up where it left off (per User Story 2's skip-what's-already-there behavior).
- What happens when an individual document's link is broken or its download fails? That document is skipped and reported; the run continues with the remaining documents rather than aborting entirely.
- What happens when a document's metadata is incomplete on the source page (e.g. no publish date shown)? The document is still downloaded and saved; the metadata record captures whatever is available and leaves the missing field blank rather than failing the whole download.
- What happens when the same document appears more than once in the listing (e.g. due to the source site's pagination shifting between requests)? It is only downloaded and recorded once.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST discover and walk every page of a given regulation category's listing on the source site, without requiring the operator to know in advance how many pages exist.
- **FR-002**: The system MUST download every regulation document PDF found in the listing, including multiple historical issues of the same section/regulation where present.
- **FR-003**: The system MUST save, for every downloaded document, a metadata record containing at minimum: title, source URL, the section/regulation the document belongs to (as stated in its title on the source site), issue/revision number, publish date, and the timestamp the document was downloaded.
- **FR-004**: The system MUST NOT re-download a document whose source URL was already successfully downloaded in a previous run.
- **FR-005**: The system MUST wait at least 10 seconds between requests to the source site, matching the site's published crawl-delay policy.
- **FR-006**: The system MUST continue processing remaining documents when an individual document fails to download, and MUST report which documents failed rather than silently dropping them.
- **FR-007**: The system MUST NOT assign a department or business category to a downloaded document — that determination is explicitly left to a later, separate step.
- **FR-008**: The system MUST NOT perform any parsing, chunking, embedding, or database ingestion of downloaded documents — its responsibility ends at fetching and saving the PDF and its metadata.
- **FR-009**: The system MUST NOT run on a recurring schedule by itself — each run is a manual, one-time invocation.

### Key Entities

- **Downloaded Document**: A single regulation PDF fetched from the source site, together with its metadata — title, source URL, section/regulation, issue/revision number, publish date, and the timestamp it was downloaded. This is the unit of work the tool produces and later checks against to avoid re-downloading.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a full run against a category with no prior archive, 100% of the regulation documents listed on the source site for that category (across all its pages) are present in the local archive.
- **SC-002**: Every document in the local archive has a complete, inspectable metadata record (title, source URL, section/regulation, issue/revision, publish date, download timestamp) alongside it.
- **SC-003**: Re-running the tool immediately after a successful full run results in zero re-downloaded documents.
- **SC-004**: A run that hits an unreachable source or a broken individual document link still leaves all previously-downloaded documents intact and produces a clear report of exactly which documents, if any, failed.

## Assumptions

- The source category listing is publicly reachable without authentication, as confirmed by inspecting the live page.
- The total number of pages/documents in a category is not fixed or known in advance and must be discovered by the tool itself at runtime.
- Downloaded PDFs and their metadata are stored locally on the machine that runs the tool; distributing or uploading the archive to shared/cloud storage is out of scope for this feature.
- The section/regulation and issue/revision information is derived from the document's title and publish-date fields as presented on the source site, since the site does not otherwise expose that information as a distinct field per document.
- Feeding downloaded documents into the existing ingestion pipeline remains a manual, separate step performed after a download run, not triggered automatically by this feature.
