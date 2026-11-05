# Changes

Changes to the records, the exports and the figures derived from them. Corrections to figures published earlier are listed first, with the old and new values, so that anyone who cited a figure can see what changed and why. The repository's history holds every earlier state.

## Unreleased (sixth pass: historical truth and attribute support, 5 November 2026; commit `a8cd1e3`)

The availability model, the 521 attribute-support rows and the review kit added by the previous audit were themselves audited before anything else was done. This entry first said that nothing was committed in the pass; the work was committed afterwards, unchanged, as `a8cd1e3`.

### Corrected figures

| Figure | Was | Now | Why |
|---|---|---|---|
| Lower bound of availability of Vistra's June 2026 report | 2026-01-09 | 2026-04-01 | The start of the period a report covers now bounds it from below, and is later than any event its rows print |
| Lower bound of Catalyst's June 2026 census | none | 2026-08-14 | The dates on which the census records receiving issuers' compliance reports now bound it from below |
| Estimate of availability of ICRA's rationale `icra-krcl-139196` | 2025-11-25, its own date | none | A file's own date is a lower bound, not an estimate. With no publisher's or server's date the file has no estimate, and the estimated view admits it only from the day it was observed, 2026-11-04 |
| Support rows for issuer identity | 153 | 52 | 71 rested on no transcribed evidence of the issuer, such as a trustee's letter printing only the ISIN, and 33 on another anchor of the same file. Which issuer an ISIN belongs to is now its own attribute |
| Rows in `attribute_support.csv` | 521 | 716 | 630 supports, 79 of which are labelled as establishing nothing, and 86 issuer-code inferences |

No status, comparison, follow-up count or timing comparison changed.

### Corrected behaviour

- **Availability is a state, not a date.** On any day a file is `not_yet_possible`, `uncertain` or `confirmed`. The estimated view no longer counts a file's own date, or its retrieval, as an estimate. Views record each admitted file's state, and a new `possible` view gives the upper envelope.
- **`brdo show --as-of`** tags every line with its file's state, says how the issuer link is known, and never shows when the project later observed a file. **`brdo status --as-of`** without `--availability` prints the observed, estimated and possible statuses side by side, and calls a status settled only where the observed and possible views agree.
- **Support rules.** A claim's or link's evidence establishes an ISIN only where its quotation prints it. An issuer's identity needs its name, a variant, its CIN or LEI, or its own website, not merely one of its ISINs. Names match as whole names, exactly or with a parenthetical addition. A CIN or LEI counts only from the issuer's own publication, a quotation naming the issuer, or a depository page for one of its ISINs.
- **Views hide what they cannot establish.** An issuer that a view cannot identify, or cannot tell from another of the same name, appears under its ISINs' issuer code, never under the dataset's identifier, which encodes its name. Before 3 November 2026 the two Samunnati issuers appear this way. ISINs that no admitted record prints are removed from the records that list them, and discrepancy descriptions are withheld as later prose.
- **The review kit.** The packet now names each line's file hash, ISINs and field kind, uses `none` for "no value" so that a blank always means undecided, and is written in two rounds chosen by field and record. `brdo review packet` refuses to write inside the repository or over an earlier round, and writes the key readable by its owner only. The scorer reports each field with the statistics its kind allows, the label distributions, and the hard cases and unsure answers apart.

### Added

- **Records:** `Source.issuer` links the six issuer websites to their issuers; `Document.robots_at_retrieval` records that ICRA's rationale was retrieved while no robots policy could be established; `AnnotationReview.second_unsure`.
- **Exports:** `attribute_support.csv` gains `basis`, `establishes`, `matched_as_reported`, `explanation` and `available_not_before`, and issuer-code inference rows. `documents.csv` renames `available_from` to `available_estimate` and `available_basis` to `available_estimate_basis`, and adds `robots_at_retrieval`. `issuers.csv` and `instruments.csv` rename `established_from` to `established_estimate` and add `established_not_before`; `instruments.csv` adds `issuer_link_basis`, `issuer_link_estimate` and `issuer_link_confirmed_by`.
- **Report sections** on what supports each entity and attribute, and on what verification needs, host by host.
- **The codebook** cites the exact SEBI file for covenant categories, with its address, SHA-256 and page.
- **Tests** for each state and view, each support rule, issuer codes and shared names, the leak of issuer identifiers into views, the packet's refusal and key permissions, the rounds, and each kind of agreement statistic.

### Not done

- `brdo fetch` and `brdo verify` could not run: the proxy refused the tunnel to every source host, and the fetcher, correctly, reported robots.txt as unread and fetched nothing. Verification figures are still those of 4 November 2026.
- No annotation was changed and no review was made. Two labels that may not follow the written rules are left for adjudication.

## Unreleased (audit of the fifth pass, 5 November 2026; commit `2094841`)

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

## Unreleased (fifth pass, 4 November 2026; commits `2f095f1`, `d37c5bd`, `caf4a42`, `f51b281`)

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
