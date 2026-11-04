# Methods

How the records in this release were made, and how far each step can be trusted.

## Search process

1. **Trustee reports.** For each trustee reviewed, the disclosure pages were opened and the report for the quarter ended 30 June 2026 retrieved. Every attempt is logged with its outcome, including the two trustees for whom none surfaced. Axis Trustee publishes several dated versions per quarter, and the two for this quarter were both taken.
2. **Trustee notices.** Catalyst's and IDBI's listing pages link letters to holders. The June-quarter letters for issuers in the sample were retrieved, plus several from other quarters where they make a point about persistence.
3. **Contract documents.** For each issuer, one web search by a specific ISIN, then for eight issuers a second search using the covenant wording the trustee quotes. The query, date and outcome are logged in `data/searches.yaml`. A hit counts as located only if the ISIN or the covenant wording ties it to the instrument.
4. **Cross-checks.** A depository page was consulted for selected ISINs where the issuer's identity or the trustee was in doubt. Values seen are recorded as observations, with the URL and date.

Not everything was searched exhaustively. A `not_found` means not found through the logged query on that date.

## Transcribing a report

1. `brdo add-document` retrieves the file through the policy-checked fetcher and records its URL, hash and dates.
2. The text layer is read page by page. Because reading order can scramble merged cells, it is compared with a layout-preserving extraction.
3. **The rendered pages are reviewed**, and only then may `extraction_complete` be set. This step exists because of an error: Vistra's report at first seemed to have no header, no first row and an unnamed issuer. Its rendered page has all of them, since the file draws those rows as outlines that extraction cannot see.
4. Each printed row becomes one record, or several where its ISINs carry different dates. Each covenant cell becomes one or more items, split where it mixes categories.
5. Quotations are cut to the source's limit, after every percentage, multiple and crore amount in the whole cell has been recorded in `levels_stated`.
6. Dates are recorded as printed and as read, and a mismatch fails validation.

Trustee notices in letter format were drafted with a one-off script that found the deed sentence, dates and clause heading, and each candidate was then reviewed. IDBI's notices and all scanned files were transcribed directly. The drafting script is not part of the repository, because the records are what is verified.

## What is checked by machine, and what is not

| Check | Catches | Does not catch |
|---|---|---|
| Schema validation | Unknown fields, invalid ISINs, a date that disagrees with its printed text, a deed date not printed in its quotation | Wrong values that are internally consistent |
| Integrity checks | Dangling references, policy breaches, a quotation over the limit, a page beyond the file, an uncited document | Whether a reference is the right one |
| Evidence verification | A quotation or number not on the cited page, a file that has changed | Words read from an image; misreading a table's structure |
| ISIN completeness | An ISIN in a report's text that was not transcribed | ISINs absent from the text layer |
| Text layer audit | Outlined text, scans, OCR layers | Other ways a text layer can differ from the page |
| Tests on the dataset | Stale exports, NSE material, a listed ISIN without `reported_breach` | Annotation quality |

A deliberately altered threshold and a deliberately altered deed date both fail verification, and an altered ISIN fails its check digit.

**Not checked by machine:** the assignment of an ISIN to a row where cells are merged, categories, specificity, action kinds, parsed limits, and plain-English notes. These come from a single pass of curation, with no independent second review. Treat them as a careful first reading, and report errors.

Fifty-five anchors rest on reading a rendered page, because the file has no usable text layer for that passage. They are reported as `visual_only`, and checking one means opening the page.

## Classifying covenants

`category` follows the categories of SEBI's guidance note (Annex-VIA of the Master Circular). Undertakings outside that list, such as information covenants and post-closing deliverables, are `other`, and a clause cited only by number with no text is `other` with a note, since the report does not show what it is. The document's own heading is kept separately.

`thresholds` are parsed only where the wording is unambiguous. Where a limit changes over time, each step is recorded with its dates. A comparator or date that is unclear is left out rather than guessed.

`explanation` is a plain-English gloss for readers, written from the quoted text alone. It is not legal advice, and it may simplify.

## Scoping

During early scoping, a few pages and documents were fetched with a general-purpose command-line client using a browser-style user agent, before BSE's refusal of identified clients had been found. Once it was found, this stopped, and those copies are not cited anywhere in the dataset. Two notes in the search log describe what scoping showed about BSE-hosted documents (that a document names an ISIN, or that it lacks a trustee's quoted wording). They are search notes rather than evidence and should be confirmed when those files are ingested. All documents in `data/documents.yaml` were retrieved by the project's fetcher under its own identity.

## Updating

Each new quarter means re-opening each trustee's listing, adding new files as new documents, and setting `supersedes` where a file replaces an earlier version. Nothing is overwritten. `brdo fetch` and `brdo verify` will show a `hash_mismatch` if a source later changes a recorded file; that should be recorded as a new document, not corrected in place.
