# Data model

The dataset is a set of attributed statements rather than a table of facts. Two sources can disagree without one overwriting the other, and an interpretation can never be mistaken for what a source said.

JSON Schemas for every record type are in [`schema/`](../schema), generated from [`models.py`](../src/brdo/models.py). Values for categorical fields come from [`vocab.py`](../src/brdo/vocab.py).

## Records

| Record | File | What it is |
|---|---|---|
| `Source` | `data/sources.yaml` | A publisher and the access and reuse policy for it |
| `Document` | `data/documents.yaml` | One exact file, identified by SHA-256. A revised file at the same URL is a new document |
| `Issuer` | `data/issuers.yaml` | A legal entity, with identifiers and the name variants found in sources |
| `Instrument` | `data/instruments/<ISIN>.yaml` | One ISIN, its attributed claims and links to documents |
| `BreachReport` | `data/breach-reports/<document>.yaml` | A transcribed trustee report, with rows and items |
| `BreachNotice` | `data/breach-notices.yaml` | A trustee's letter about one instrument: deed dates, dates of intimation, meetings, adjournments |
| `Provision` | `data/provisions/<document>.yaml` | One contractual undertaking, quoted, with parsed limits where unambiguous |
| `ComplianceStatement` | `data/compliance-statements.yaml` | An explicit statement about compliance for stated instruments and a period, with who made it, what it covers and its exception lines |
| `MonitoringCensus` | `data/monitoring-censuses.yaml` | A trustee's table of the issues it monitors, kept as measurements: the count of ISINs it prints, listed ISINs it omits, a reproducible sample, and cited rows with receipt dates |
| `RegulatoryReference` | `data/regulatory-references.yaml` | A checked passage of a regulatory text that the design relies on |
| `SearchRecord` | `data/searches.yaml` | One documented attempt to find something, including failures |
| `Discrepancy` | `data/discrepancies.yaml` | A disagreement or oddity, kept open until resolved |

## How the entities relate

```
Issuer ─< Instrument (ISIN) >─< Document
                │                  │
                │                  ├─ BreachReport ─< BreachRow ─< BreachItem ──> Provision
                │                  ├─ BreachNotice (deed dates, clause, meeting)
                │                  └─ Provision (amends → earlier Provision)
                ├─ Claim (who says what about it)
                └─ derived status per reporting period
```

- **Issuer, issue and ISIN are not interchangeable.** SEBI's circular says one ISIN may span several offer documents, and one document may cover several ISINs, so documents and instruments are many-to-many. INE982X08109 has five trust deed dates in one notice.
- **Linking carries its reason.** `DocumentLink.basis` records why a document is tied to an ISIN (the ISIN is printed, an exchange notice says so, a trustee report lists it, or attributes match). An ISIN appearing in a document's list of outstanding debt does not make that document its contract.

## Evidence

An `Evidence` anchor names a document, a 1-based page of the file (not the printed page number), and optionally a verbatim quotation. Every field ending in `_as_reported`, every printed date and every ISIN in a report row becomes an anchor automatically, so transcription can be tested.

`brdo verify` tries the following in order and reports which one worked:

| Result | Meaning |
|---|---|
| `verified:normalized` | The quotation occurs on the page after folding case, spacing, typographic punctuation and mis-mapped ligatures |
| `verified:spaceless` | It occurs once all spaces are removed, which handles words broken by extraction |
| `verified:token_sequence` | Its words occur in order with at most 12 other words between neighbours, which handles interleaved table columns |
| `visual_only` | It is not in the text layer and the record says it was read from the rendered page. Reported separately and never counted as machine-verified. If the cited page has no text layer at all, finding the same words on another page does not count against it |
| `wrong_page`, `not_found`, `page_out_of_range` | Failures |
| `hash_mismatch` | The file differs from the recorded hash, whether in the cache or at the source |
| `document_unavailable` | The file could not be obtained, and nothing has been checked |

It also audits each page's text layer, flagging text drawn as vector outlines, scanned pages and OCR layers, and fails if a transcribed report's text prints an ISIN that the transcription lacks.

## Statements by issuers and auditors

A `ComplianceStatement` separates the publisher (`stated_by`, a source) from the maker (`made_by`: `issuer` or `statutory_auditor`). It also records what the statement says it covers (`scope`: `all_covenants` or `financial_covenants`). Its `exceptions` are the lines the statement lists as not met, each with the ISINs, the covenant as printed, and the required and actual levels or deed dates where printed. Every one of those fields is an evidence anchor.

`isins_printed` is false when the statement reaches an ISIN only by a general sentence about all listed debentures, or by leaving it off its list of exceptions. A statement that lists exceptions must state a breach, and its exceptions may only name its own instruments.

`brdo report` sets each statement beside the trustee's current report for the same quarter (`statement_report_comparisons.csv`):

| Agreement | When |
|---|---|
| `consistent` | Both report a breach; or the statement reports compliance and a fully transcribed trustee report does not list the ISIN |
| `differs` | The statement reports compliance and the trustee lists a breach it covers; or the statement reports a breach that a fully transcribed trustee report does not list |
| `not_comparable` | No fully transcribed report of the ISIN's trustee exists for the period; or the statement covers financial covenants only and the trustee lists another kind |

The comparison also lists required levels that the statement prints and the trustee's report does not print for that ISIN. It records lineage too: the statement's date, the date the trustee records receiving the issuer's compliance report (from a census, where measured), the trustee's date of detection, and whether the trustee's row cites a certificate. `trustee_could_rely_on_issuer` is true when the detection is on or after one of the earlier dates. Agreement in such cases is transmission, not independent confirmation.

## Clause records and their legal stage

`Provision.stage` says what a clause record is evidence of:

| Stage | Meaning |
|---|---|
| `executed_text` | Quoted from the executed deed, supplemental deed or offer document |
| `described_in_force` | A party's description of a term it treats as in force (the default) |
| `proposed` | A change put forward for approval |
| `approved_in_principle` | A proposed change approved in principle, for example by an exchange, not shown executed |

Only executed text establishes an operative term.

## Point-in-time views

When a file became public is never known exactly, so `pit.availability` gives each file three dates and keeps them apart:

| Date | Meaning | Proves |
|---|---|---|
| `available_not_before` | The latest date the file gives itself, its signature, its "as on" date, or a letter transcribed from it. It cannot have been public earlier | A lower bound |
| `available_from` | The estimate: the later of the publisher's own date (a listing page) and the server's Last-Modified header for the exact file held, never before the lower bound. Failing both, the lower bound itself; failing that, the observation | Nothing; Last-Modified dates the version on the server, and a copied file can carry a misleading date |
| `available_observed` | The day the project retrieved the file from its public address | That the file was public by then |

`pit.as_of(dataset, day, mode)` keeps only what the chosen dates show public by `day`. `mode` is `estimated` (the default) or `observed`, which admits a file only from the day the project saw it, so nothing can count too early. Every record whose document is withheld goes. So does every claim, document link, issuer name variant and discrepancy whose support was not yet public, and every observation made after `day`; the evidence lists of what remains are cut to what was public. The search log is kept whole, because it records the project's own steps. A report that a logged search later found, but that the view withholds, gives `no_report_found` with basis `trustee_report_not_yet_public`, never `trustee_report_not_searched`. The view records its `cutoff`, its mode and the documents it `withheld`. A test rebuilds the view at every date on which some document's availability changes, in both modes, and fails if anything later leaks in.

This is the record as it stood, not as the project knew it on that day. For what the dataset itself said at an earlier time, use the repository's history.

## What each party adds, and follow-up states

`consistency.field_flows` records, for each agreement between an issuer's statement and a trustee's report, whether each party prints a clause reference, the obligation's wording, a required level, the issuer's measured level and deed dates, and the text that satisfied each rule. `consistency.follow_up_states` lists every follow-up state per trustee and listed ISIN with the row or letter behind it, never ranking or merging them. It types a cure by the covenant category of its row, so a late filing made good is never counted as a financial covenant restored. It does not count a letter that names another quarter. The report prints, beside every count of ISINs, the number of issuers behind it, because one issuer's ISINs share one history.

## Trustee censuses

A `MonitoringCensus` is not a copy of the trustee's table. It holds the file's identity, `isins_printed`, `listed_not_printed`, a `sample` and the `entries` the analysis cites. `report_not_received` lists ISINs whose rows mark the issuer's quarterly compliance report as not received. `brdo verify` recomputes the count, the omissions, that list and the sample from the hashed file and fails if they differ. The sample is the 20 ISINs, outside the trustee's breach report for the period, whose SHA-256 of the file's hash, a colon and the ISIN sorts first, so it can be reproduced without this code.

## Dates

A date is never just a date. Records keep distinct fields for what each one means.

| Meaning | Where |
|---|---|
| When a document dates itself or was signed | `Document.dates`, kinds `dated` and `signed` |
| When the publisher says it was published, for example on a listing page | `Document.dates`, kind `published`, never from a server header |
| When the server says the exact file held was last modified | `Document.dates`, kind `last_modified`, basis `http_last_modified` |
| When the project retrieved it, and whether by pipeline or by hand | `Document.retrieved_at`, `Document.retrieved_manually` |
| When it was public: lower bound, estimate and observation | Derived by `pit.availability`; see Point-in-time views |
| The reporting period, and a report's "as on" date | `Document.period`, `Document.as_of` |
| Date of actual breach, as printed and as read | `BreachRow.actual_breach` (`raw`, `value`, `note`) |
| Date of detection, as printed and as read | `BreachRow.detected` |
| Each intimation and to whom | `BreachRow.intimations` |
| When the issuer told the trustee, per its notice | `BreachNotice.issuer_intimation` |
| When a limit applies | `Threshold.applies_from`, `applies_to` |

A value must match its printed text, or a note must explain why it does not. Trustees define "actual breach" differently, so printed definitions are kept in `BreachReport.printed_notes`.

## Separating source text from interpretation

| Kind | Fields |
|---|---|
| Source text, verbatim | `*_as_reported`, `Provision.text`, `Evidence.quote`, `ReportedDate.raw` |
| Facts read from the source | ISINs, `levels_stated`, parsed dates, `deed_dates`, `Intimation` |
| Project annotation | `category`, `specificity`, `actions`, `metric`, `thresholds`, `explanation`, `ProvisionLink` |
| Derived mechanically | status, comparisons, revisions, every figure in the report |

`Provision.annotation_reviewed` is false until a second review has taken place; in this release it is false for all clauses.

## Status per ISIN and period

Status answers one question: what does the reviewed record say about breaches for this ISIN and period? `brdo status` derives it in a fixed order, and `basis` records which rule applied.

| Status | Basis | Rule |
|---|---|---|
| `reported_breach` | `listed_in_current_version` | The current version of a report lists the ISIN |
| | `listed_as_carried_over` | It is listed, but the row's own label assigns it to an earlier quarter |
| | `named_in_trustee_notice` | A trustee's notice for that quarter names it |
| | `explicit_statement` | An explicit statement says a breach occurred |
| `reported_no_breach` | `explicit_statement` | An explicit statement covers it, and none disagrees |
| `no_information_reported` | `issuer_named_as_no_information` | The trustee says it has received no information about the issuer |
| `no_report_found` | `not_listed_in_trustee_report` | Its trustee's fully transcribed report does not list it |
| | `trustee_report_is_nil` | Its trustee's report is a nil table |
| | `trustee_report_not_located` | A logged search did not find its trustee's report |
| | `trustee_report_not_yet_public` | In a point-in-time view only: a logged search later found its trustee's report, but the report was not shown public by the view's date |
| `inaccessible` | `trustee_report_not_accessible` | The report could not be reached, or policy excludes it |
| `ambiguous` | `listing_depends_on_layout` | Listing depends on reading merged table cells |
| | `trustee_not_established` | Sources disagree on the trustee, and at least one candidate's report was reviewed |
| `conflicting` | `listed_only_in_earlier_version` | An earlier version lists it and the current one does not |
| | `statements_disagree` | A statement of compliance whose scope covers a listed covenant, or two statements, disagree |
| `not_assessed` | `trustee_unknown` | No source names its trustee |
| | `trustee_report_incompletely_transcribed` | The report exists but was only partly transcribed |
| | `trustee_report_not_searched` | Nobody has looked |

**The categories are never merged, and none implies another.** In particular:

- `no_report_found` is not compliance, and a nil table is not an explicit statement.
- A rating downgrade, a worsening ratio or a late filing does not produce `reported_breach` unless a source says a breach occurred.
- `reported_no_breach` records someone's statement, which the project does not adopt.

A full report transcription can only claim completeness if its rendered pages were reviewed, since a text layer can silently omit content.

## Identifiers

ISINs are validated with their check digit, and CINs and LEIs by format and check digit where one exists. The ISIN's issuer code is used as a consistency check. Other records use stable lowercase slugs, such as `ctl-t5-2026-06` for Catalyst's Table 5 report for June 2026.

## Exports

`brdo build` writes one CSV per table in [`exports/`](../exports), and optionally SQLite. All formats are computed from the same `tables()` function and are deterministic. Multi-valued cells are joined with `; `.

Every column is described in [data-dictionary.md](data-dictionary.md), generated from `src/brdo/dictionary.py`, and in `exports/datapackage.json`, a Frictionless Data Package descriptor for use outside this repository. Each column has one kind:

- `identifier`;
- `source_text`, which is quoted and not licensed;
- `read_from_source`;
- `annotation`, which is single-pass;
- `derived`;
- `provenance`.

Where a fact originates with a party other than its publisher, the dictionary says so. A test fails if any exported column is undocumented.

`field_flows.csv` and `follow_up_states.csv` export the field-level comparison and the follow-up states, with the text, row or letter behind each decision.
