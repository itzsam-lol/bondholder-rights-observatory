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

## Issuers' own statements

For the quarter ended 30 June 2026, the issuer's statement of covenant compliance was sought for 11 issuers in the sample, mostly lenders whose trustees print covenant levels. Every query and outcome is in `data/searches.yaml` under `compliance_statement`.

1. A web search by issuer name, "security cover certificate" and the quarter, then, for two issuers, the regulation 62 disclosure page on the issuer's own site. The second is the better protocol, and the one future quarters should use.
2. Candidates were previewed through the same policy-checked fetcher before being registered. Each issuer website was registered as a source only after reading its robots.txt and its terms. Where a site refused the project's identified client, the files were logged as located but not retrieved and the site was marked manual only.
3. Statements were transcribed from rendered pages where the annexure is a scan or carries an OCR layer, and the record says so (`visual_fallback`). One scan prints an ISIN with an "F" where the other lines of the same table print "E"; it is read as the ISIN the table prints elsewhere, and the note says so.
4. Who made the statement (the issuer or its statutory auditor) and what it says it covers (all covenants, or financial covenants only) are recorded as printed. An auditor's limited-assurance conclusion is quoted together with its negative form, because the operative clause alone reverses its meaning.
5. Identifiers in a statement that are outside this dataset, such as bonds listed in IFSC, are left out and mentioned in the note.
6. Several compliance reports also print lists of individual debenture holders. Nothing from those pages is recorded.

## Trustee censuses

Catalyst publishes, for each quarter, a table of the quarterly compliance reports, financial statements and performance reports it has received. The table lists every monitored issue by company and ISIN, with the date of receipt and any delay. It is the trustee's version of Annex-VIIA, Table 3. The table for the quarter ended 30 June 2026 was retrieved through the pipeline and is identified by its hash.

- **The census is measured, not transcribed.** `isins_printed` counts the distinct ISINs in the file's text that pass the check digit. One printed identifier fails it and is not counted.
- **Omissions are recorded.** `listed_not_printed` names ISINs in the trustee's breach report for the quarter that the census omits.
- **The sample is drawn by a fixed rule.** The ISINs outside the breach report are ranked by the SHA-256 of the file's hash, a colon and the ISIN, and the first 20 are taken. Anyone with the same file can reproduce the selection by hand.
- **Only the rows the analysis relies on are quoted,** those giving receipt dates for ISINs whose issuer statements are compared.
- `brdo verify` recomputes the count, the omissions and the sample from the cached file and fails on any difference.

Row-by-row parsing of the table was tried and set aside. Serial numbers restart, cells run across rows, and date formats vary, so a parser would have needed a rule for every irregularity. The count of printed ISINs and a lookup of specific rows do not depend on the layout.

## Lineage of agreements

For each comparison between an issuer's statement and a trustee's report, the dataset records the statement's printed date, the trustee's recorded receipt of the issuer's compliance report where a census has been measured, the trustee's printed date of detection, and whether the trustee's row cites a certificate or auditor. These are facts read from the documents. The inference drawn from them, that an agreement may be transmission rather than confirmation, is the project's, and the report states it as such.

## What each party adds

The field-level comparison uses mechanical rules, so that it can be re-run and challenged. `exports/field_flows.csv` gives, for each decision, the text that satisfied the rule:

- **Clause reference:** a named clause, schedule, paragraph, section or article, or a numbered paragraph opening the text. On the trustee's side, a clause reference transcribed from the row also counts. A bare decimal elsewhere, such as a measured level of "-1.02%", is not a reference; an earlier version of the rule counted it as one, and was corrected after each decision was checked by hand.
- **Obligation wording:** a verb such as "shall", "maintain", "ensure", "not exceed" or "at least". On the trustee's side it also needs an item marked as clause text.
- **The issuer's measured level:** credited to the trustee only if the trustee prints the same number and unit.
- **Deed dates:** on the trustee's side, from its letters for the quarter.

## Availability dates

Three dates are kept for each file (see [data-model.md](data-model.md#point-in-time-views)):

- **A lower bound** from the file's own dates and the letters in it.
- **An estimate** from the publisher's listing date or the server's Last-Modified header, whichever is later.
- **An observation**, the day the project retrieved the file.

A Last-Modified header is recorded as `last_modified` and never as a publication date. It describes the version held, which may be later than the first publication. A copied file can also carry a date unrelated to its publication. Timing figures are therefore measurements of the files held, not findings about anyone's timeliness. Every observation in this release falls on 3 or 4 November 2026, so the project can prove nothing about what was public before then. The estimates are the only basis for earlier dates.

## Follow-up states

Each state comes from the project's reading of a report's action cells, or from the trustee's letters naming the ISIN. A letter that names another quarter is not counted for this one. A letter continuing an adjourned meeting names no quarter, and counts for the ISIN it names. `exports/follow_up_states.csv` lists every state with the row or letter that shows it.

## The comparison sample

The first pilot searched for the June 2026 covenant statement of four sampled issuers, and checked one issuer's own debenture pages. Under the NSE policy, no URL on NSE is recorded, even when a search surfaced one.

## What is checked by machine, and what is not

| Check | Catches | Does not catch |
|---|---|---|
| Schema validation | Unknown fields, invalid ISINs, a date that disagrees with its printed text, a deed date not printed in its quotation | Wrong values that are internally consistent |
| Integrity checks | Dangling references, policy breaches, a quotation over the limit, a page beyond the file, an uncited document | Whether a reference is the right one |
| Evidence verification | A quotation or number not on the cited page, a file that has changed | Words read from an image; misreading a table's structure |
| ISIN completeness | An ISIN in a report's text that was not transcribed | ISINs absent from the text layer |
| Text layer audit | Outlined text, scans, OCR layers | Other ways a text layer can differ from the page |
| Tests on the dataset | Stale exports, NSE material, a listed ISIN without `reported_breach` or a disagreeing statement, e-mail addresses, depository participant IDs, PANs and written-out phone numbers in the published records | Annotation quality; personal data in forms the patterns do not cover |
| Point-in-time test | A record, claim, observation or status document in a view of a date that its evidence was not shown public by, at every date where availability changes and in both modes | Wrong availability dates themselves |
| Data dictionary test | An exported column with no description or kind | A description that is wrong |

A deliberately altered threshold and a deliberately altered deed date both fail verification, and an altered ISIN fails its check digit.

**Not checked by machine:** the assignment of an ISIN to a row where cells are merged, categories, specificity, action kinds, parsed limits, and plain-English notes. These come from a single pass of curation, with no independent second review. Treat them as a careful first reading, and report errors.

At the last full run of `brdo verify`, on 4 November 2026, 107 anchors rested on reading a rendered page, because the file has no usable text layer for that passage. They are reported as `visual_only`, and checking one means opening the page. `evidence.csv` marks every anchor recorded as read from the rendering (`read_from_rendering`). Not all of them are `visual_only`, because some of their words are found in the text layer anyway. See [reliability.md](reliability.md) for what has and has not been checked, and the rules a second annotator should apply.

## Classifying covenants

`category` follows the categories of SEBI's guidance note (Annex-VIA of the Master Circular). Undertakings outside that list, such as information covenants and post-closing deliverables, are `other`, and a clause cited only by number with no text is `other` with a note, since the report does not show what it is. The document's own heading is kept separately.

`thresholds` are parsed only where the wording is unambiguous. Where a limit changes over time, each step is recorded with its dates. A comparator or date that is unclear is left out rather than guessed.

`explanation` is a plain-English gloss for readers, written from the quoted text alone. It is not legal advice, and it may simplify.

## Scoping

During early scoping, a few pages and documents were fetched with a general-purpose command-line client using a browser-style user agent, before BSE's refusal of identified clients had been found. Once it was found, this stopped, and those copies are not cited anywhere in the dataset. Two notes in the search log describe what scoping showed about BSE-hosted documents (that a document names an ISIN, or that it lacks a trustee's quoted wording). They are search notes rather than evidence and should be confirmed when those files are ingested. All documents in `data/documents.yaml` were retrieved by the project's fetcher under its own identity.

## Updating

Each new quarter means re-opening each trustee's listing, adding new files as new documents, and setting `supersedes` where a file replaces an earlier version. Nothing is overwritten. `brdo fetch` and `brdo verify` will show a `hash_mismatch` if a source later changes a recorded file; that should be recorded as a new document, not corrected in place.
