# Changes

Changes to the records, the exports and the figures derived from them. Corrections to figures published earlier are listed first, with the old and new values, so that anyone who cited a figure can see what changed and why. The repository's history holds every earlier state.

## Unreleased (audit of the fifth pass, 5 November 2026)

The fifth pass's own changes were re-examined before anything was added. This entry corrects that pass where it was wrong, including two claims in its entry below.

### Corrected figures

| Figure | Was | Now | Why |
|---|---|---|---|
| Catalyst ISINs with a meeting adjourned for lack of quorum, quarter ended 30 June 2026 | 15 (3 issuers) | 14 (3) | A letter continuing an adjourned meeting states no quarter, and was counted for whichever quarter was asked about. It now counts only where a stated rule ties it to an earlier letter of the same file. The letter for INE179P07530 (`ctl-notice-dvara-2026-08-p9`) cannot be tied, and its 2 states are exported with no quarter |
| Catalyst ISINs with a meeting reported as scheduled | 39 (12) | 38 (12) | The same correction |
| Lower bound of availability ("not public before") of the June 2026 breach reports of Catalyst, IDBI and Vistra | Blank | 2026-09-11, 2026-09-15 and 2026-01-09 | A report cannot have been public before an event it records. The latest detection, breach or intimation date that its rows print now bounds it from below. No estimate changed |

No other published figure changed. The field-level comparison, cure counts, estimates of availability and the timing comparisons built on them are as before.

### Corrected behaviour and wording

- **Point-in-time views.** The fifth pass said that nothing later than the date appears. That was not so. Every instrument and issuer appeared in every view, with its base name, CIN, LEI and sector. Notes and searches written later were kept, and a `withheld` list named what was left out. Now an entity or attribute appears only when a record then public supports it, sector never, later notes and searches are dropped, and no such list exists.
- **"Not yet public" withdrawn.** The fifth pass gave `no_report_found` with basis `trustee_report_not_yet_public` when a later search found a report that a view left out. A later search cannot show that a report was not public earlier. An estimated view now gives `not_assessed` with basis `trustee_report_not_in_view`, saying only that the view holds no report. An observed view and the full record give `trustee_report_not_searched`.
- **Cures** are typed only when every covenant the row lists for the ISIN is of one kind, not by any one covenant of the row. Otherwise they are "cure reported, for covenants of more than one kind". No row mixes kinds, so no figure changed.
- **Field flows** keep every supporting line, with document, page, locator and the number of lines examined, not only the first match. 22 of the 85 decisions rest on more than one line.
- **The clause-reference rule** needs the word clause, schedule, paragraph or article followed by an identifier, or a transcribed clause number. A bare numbered heading, a decimal and the word "section" no longer count. 30 hand-written cases pin the rule. No figure changed.
- **Legal stages.** `executed_text` was defined as quoted from "the executed trust deed, supplemental deed or offer document", and the report's last step counted an offer document as "the contract itself". An offer document is now its own stage, `offered`, and validation checks each stage against the document type. `instruments.csv` replaces `contract_documents` with `offer_documents` and `executed_deeds`, and the report counts each separately. No record was affected.
- **robots.txt.** A refusal at the robots address (401, 403, 406, 429, 451 and every other status except 404 and 410), or an HTML page where the file should be, was treated as no robots file, so retrieval went ahead. Now only a robots file, or a 404 or 410, settles the policy. Anything else stops retrieval from the host and is reported as robots.txt being unread, never as a refusal. ICRA's rationale `icra-krcl-139196` was retrieved by the pipeline on 4 November 2026 while ICRA's robots address returned a bot-mitigation page; under the corrected rule it would not have been fetched. The record is unchanged.
- **SEBI's circular of 25 February 2022.** `docs/exchange-access.md` said that a secondary index described it as subsumed into a master circular, and that its current form was not checked. SEBI's master circulars show that it is rescinded only for some intermediaries, whose master circulars reproduce its paragraph 4. No rescission for exchanges, depositories or debenture trustees was found.
- **NSE's terms.** The source record says that NSE's hyperlinking policy requires permission for links. The policy as read on 5 November 2026 says nothing of the kind, and the record's quoted prohibition of automated collection matches the terms of an NSE Data platform word for word. Neither reading was complete. The exclusion stands until a person reads the pages in a browser, and the documents now say so.
- **The report's account of availability** names every source of a lower bound, including events a report's rows record, and says that an estimate is never earlier than the lower bound.
- **Licences.** `LICENSE-DATA.md` and the README say that neither licence covers quotations, document titles or trade names, wherever they appear, including in code, tests and documentation.

### Added

- **`exports/attribute_support.csv`**: 521 rows, one for each record that supports an instrument, an issuer, a name, a CIN or an LEI, with when that record became public. `issuers.csv` and `instruments.csv` gain `established_from` and `established_confirmed_by`.
- **New columns.** `documents.csv`: `available_not_before_basis`, `available_confirmed_by` (replacing `available_observed`) and `available_window_days`. `field_flows.csv`: `issuer_evidence`, `trustee_evidence`, `issuer_examined`, `trustee_examined` (replacing `issuer_basis` and `trustee_basis`). `follow_up_states.csv`: `attribution`.
- **`exports/datapackage.json`** marks for each field whether the project's licence covers it, with rights notes, origin and what an empty cell means, and lists the cited sources. CI validates the package with an independent implementation, Frictionless 5.18.1. All 23 resources are valid.
- **A blind second-annotation kit.** `brdo review packet` writes the 585 annotated decisions, or chosen fields, without their current values, under ids fresh for each round, with 23 hard cases flagged from the text alone, and the key in a separate directory. `brdo review score` reports agreement and Cohen's kappa per field and lists every disagreement. `docs/annotation-codebook.md` states the rules, without the current labels.
- **Review records.** `AnnotationReview` (and `schema/AnnotationReview.json`) keeps the original, second and adjudicated values with reasons. Only a person other than the original annotator can make one: `second_by` accepts only `person`. `Provision.annotation_reviewed` is an error unless such reviews settle every decision of the record. No review exists.
- **Documentation.** `docs/exchange-access.md` separates six questions (access, retention, derived measurements, source-linked annotations, redistribution of documents, reuse under the project's licence), reads the 2 GB allowance as conditional, and records what Bond Central showed. `docs/coverage.md` sets out the legal stage of each candidate document and keeps the analyses' populations apart. `docs/reliability.md` gives the review protocol and the hard cases as currently annotated, including SEBI's annex listing security cover under "Affirmative".
- **Tests** for each correction: views at every availability change in both modes; continuation links; cure typing; every supporting line kept; the clause-reference cases; stage against document type; robots answers; packets that never carry a current value; kappa; and the review rules.

### Not done

- `brdo fetch` and `brdo verify` were not run, because the sources were unreachable from the environment used. Verification figures are carried forward from 4 November 2026.
- No record in `data/` was added, changed or removed.
- No second annotation was made, and no annotation is marked reviewed.

## Unreleased (fifth pass, 4 November 2026)

### Corrected

| Figure | Was | Now | Why |
|---|---|---|---|
| What each party adds: clause reference printed only by the trustee | 10 | 9 | The rule read the measured level "-1.02%" printed for INE179P07589 as a numbered clause |
| The same row: printed by neither | 1 | 2 | The same correction |
| IDBI ISINs with a holders' meeting reported as scheduled, quarter ended 30 June 2026 | 22 | 20 | A letter about the March 2026 quarter was counted as June-quarter follow-up for two PVP Ventures ISINs |
| `brdo show` and `brdo status` with `--as-of` | Claims, observations and name variants supported only by later documents appeared in views of earlier dates; a report not yet public was labelled `trustee_report_not_searched` | Nothing later than the date appears; such a report gives `no_report_found` with basis `trustee_report_not_yet_public` | Only document-level records were filtered |
| `documents.csv` column `published` | The server's Last-Modified date, for 44 of 45 documents | Only dates the publisher states: Beacon's listing date, the one such date recorded | A Last-Modified header dates the file version held, not its publication |
| Anchors resting on the rendered page, in `docs/methods.md` | 105 | 107, the figure at the last full verification run | `methods.md` was not updated when the README was |

No other derived figure changed. The statement that the issuers' statements were public before the trustees' reports in all 21 comparisons stands, but it now says that it rests on servers' Last-Modified dates. The project's own observations cannot order them.

### Changed

- **Records:** 44 dates in `data/documents.yaml` that came from a server's Last-Modified header are now of kind `last_modified`, not `published`. Validation rejects a publication date resting on a server header.
- **Availability** is kept as three dates, which `pit.availability` returns:
  - a lower bound from the file's own dates and the letters in it;
  - an estimate from the publisher's or the server's date, whichever is later;
  - the day the project observed the file.
- **Point-in-time views** (`pit.as_of`) prune every record type, and can trust observations only (`--availability observed`).
- **Follow-up states** no longer count a letter that names another quarter.
- **The fetcher** reports a robots.txt it cannot read as a failure to read it, and still fetches nothing. It used to report it as "disallowed by robots.txt", a restriction the site never stated.
- **The report** prints the number of issuers beside counts of ISINs in the comparison and follow-up tables, and gives all three availability dates for each breach report.

### Added

- **New exports:** `exports/field_flows.csv` and `exports/follow_up_states.csv`, each decision with the text, row or letter behind it.
- **New columns:**
  - `documents.csv`: `retrieved_manually`, `source_retrieval_policy`, `signed`, `last_modified`, `available_not_before`, `available_observed`;
  - `sources.csv`: `quote_limit`, `domains` (empty for sources whose policy forbids links), `notes`;
  - `evidence.csv`: `read_from_rendering`;
  - `monitoring_censuses.csv`: `report_not_received`.
- **The data dictionary** (`docs/data-dictionary.md`, from `brdo dictionary`) and `exports/datapackage.json` describe every column, its kind, and where it differs from the publisher, its origin.
- **New tests:**
  - every exported column is documented;
  - no point-in-time view holds anything later than its date;
  - known false positives of the comparison rules stay fixed;
  - unreadable robots files are reported as such;
  - no NSE address appears in the exports or the documentation.
- **New documents:**
  - `docs/reliability.md`: what was checked, what each finding rests on, and the annotation guide;
  - `docs/coverage.md`: biases and document gaps;
  - `docs/exchange-access.md`: formal research access under SEBI's circular of 20 December 2024;
  - `docs/legal-review-brief.md`: questions for a lawyer.

### Not done in this pass

- `brdo verify` was not re-run. The sources were unreachable from the environment used, so the verification figures are carried forward from the last run.
- No document was added, and no annotation was changed.

## Earlier passes (3 and 4 November 2026)

| Pass | Commits | What it did |
|---|---|---|
| First | `c64551c`, `2f7d2b8`, `24ed3e5`, `6ab0d0b` | Evidence-checked record pipeline; June 2026 quarter records for 95 ISINs from six trustees; research design, landscape, source policy and methods |
| Second | `9e7622b`, `8f341ad`, `f1e1bad`, `9efae3d` | Issuers' and auditors' covenant statements beside trustees' reports; a regulation 59 amendment trail; the research agenda |
| Third | `e0c65fe`, `55c6e25` | Lineage of each comparison; legal stage of clause records; Catalyst's census as a denominator and sampling frame |
| Fourth | `1810d80`, `b59975e`, `c8d8a1c` | What each party adds; typed follow-up states; availability dates and point-in-time views; compliance reports not received; the comparison-sample pilot |
