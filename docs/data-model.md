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
| `ComplianceStatement` | `data/compliance-statements.yaml` | An explicit statement about compliance for stated instruments and a period |
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
| `visual_only` | It is not in the text layer and the record says it was read from the rendered page. Reported separately and never counted as machine-verified |
| `wrong_page`, `not_found`, `page_out_of_range` | Failures |
| `hash_mismatch` | The file differs from the recorded hash, whether in the cache or at the source |
| `document_unavailable` | The file could not be obtained, and nothing has been checked |

It also audits each page's text layer, flagging text drawn as vector outlines, scanned pages and OCR layers, and fails if a transcribed report's text prints an ISIN that the transcription lacks.

## Dates

A date is never just a date. Records keep distinct fields for what each one means.

| Meaning | Where |
|---|---|
| When a document dates itself, was signed or was published, and how that is known | `Document.dates` (`kind`, `basis`) |
| When the project retrieved it | `Document.retrieved_at` |
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
| `inaccessible` | `trustee_report_not_accessible` | The report could not be reached, or policy excludes it |
| `ambiguous` | `listing_depends_on_layout` | Listing depends on reading merged table cells |
| | `trustee_not_established` | Sources disagree on the trustee, and at least one candidate's report was reviewed |
| `conflicting` | `listed_only_in_earlier_version` | An earlier version lists it and the current one does not |
| | `statements_disagree` | A statement and a listing, or two statements, disagree |
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
