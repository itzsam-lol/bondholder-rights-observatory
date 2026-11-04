# Bondholder Rights & Disclosure Observatory

An independent, evidence-backed record of what Indian listed corporate bonds promise, and of what later becomes publicly known about those promises.

A bond's protections sit in a trust deed. What happens to them afterwards is scattered across trustee websites, exchange filings and rating rationales. This project connects the two at the level of the individual ISIN:

```
Issuer → ISIN → Trust deeds → Clause → Trustee report and notice → Reported action → Original page
```

Every statement in the dataset says who made it and points to a hashed file, a page and the words relied on. A checker re-tests all of those pointers against the source files, so the record can be audited rather than trusted.

> **This is not investment advice, and it makes no finding about anyone's compliance.** A record that a trustee reported a breach means exactly that: the trustee reported it. The absence of a report is not evidence that no breach occurred.

## An example

```console
$ brdo show INE179P08082
INE179P08082  Dvara Kshetriya Gramin Financial Services Private Limited
  claim  debenture_trustee: catalyst-trusteeship  (asserted by catalyst-trusteeship)
  clause dvara-reg54-2026-02-11 Not given in the filing p8 [financial]
  clause ctl-notice-dvara-2026-08 Clause no. 17.4 (a) (iii) p11 [financial]
  report ctl-t5-2026-06 row 12: (iii) commencing from the Effective Date (DTD) until the Final Settlement Date, ...
  notice ctl-notice-dvara-2026-08 p11 2026-08-27 [breach]; deeds: 2025-05-06, 2026-07-29
  notice ctl-notice-dvara-2026-08 p14 2026-09-24 [meeting_continuation]; deeds: none cited
  open   dvara-cost-to-income-limit: Three public statements of one covenant differ. ...
  status 2025-12-31: reported_breach (explicit_statement)
  status 2026-06-30: reported_breach (listed_in_current_version)
```

For this one instrument, public documents print a cost-to-income limit of `<=70%` (the issuer, December 2025), "less than 80%" until final settlement (the trustee's quarterly report) and "less than or equal to 80%" until 30 September 2026 (the same trustee's notice, citing an amendment deed of 29 July 2026). The dataset keeps all three and the disagreement between them. It does not pick a winner.

## What this release contains

The sample starts from the quarterly covenant-breach reports that SEBI requires debenture trustees to publish (Annex-VIIA, Table 5), for the quarter ended 30 June 2026.

| | |
|---|---|
| Trustees with a logged search | 8; a report was found for 6 |
| Breach reports transcribed | 8 files, including two versions of one quarter and one later as-of report |
| Instruments | 95 ISINs of 29 issuers; 93 are listed in a report |
| Trustee notices and letters | 66 records from 23 files, giving trust deed dates and clause references |
| Contract clauses | 23, with parsed limits where the wording is unambiguous and plain-English notes |
| Search log | 48 attempts, successful or not |
| Open discrepancies | 14 |
| Evidence anchors | 1,033: 978 verified by machine against the file's text, 55 read from the rendered page |

The full, generated measurements are in the [observability report](docs/observability-report.md).

## What the first pass found

These describe this sample, which is selected on a breach having been reported. They do not describe the market.

- **Clause-level information is often public, in an unexpected place.** Trustees' letters to holders tie an ISIN to its trust deed dates and clause. A trustee states the deed date for 52 of the 93 listed ISINs, without the deed itself being needed.
- **Contracts are public to a browser but not to a program.** BSE refuses identified automated clients, NSE's terms forbid automated collection and even unapproved links, and a bond platform's terms forbid extraction tools. Of 38 logged searches for a contract document, 29 found none, and no contract could be retrieved through the pipeline.
- **Trustees' disclosures carry very different amounts of the contract.** One trustee prints the clause text for nearly every ISIN. Others mostly print a description such as "Non submission of financial results".
- **The same column means different things.** "Date of actual breach" is defined differently by different trustees, and is used in two ways within a single report, so an interval from one report cannot be compared with another.
- **Numbers agree where they can be checked.** Wherever a trustee's notice prints a level (24 comparisons), it matches that trustee's report. Detection dates match the stated date of intimation in 37 of 41. Differences of wording and duration around the same number do exist, and a numeric check cannot see them.
- **Disclosures change without notice.** Only a reader who kept both versions of one report can see that a "seeking instructions" became a reported waiver.
- **Holders' meetings fail.** Follow-up letters say a meeting was adjourned for lack of quorum for 15 ISINs.
- **Text extraction alone misreads these documents.** One report draws most of its text as vector outlines, so extraction silently loses whole rows. Others are scans. The pipeline now detects both, and a report cannot be marked complete unless its rendered pages were reviewed.

The research question, method and threats to validity are in [docs/research-design.md](docs/research-design.md).

## Using the data

Flat files are in [`exports/`](exports), and the records they are built from are in [`data/`](data).

| File | Contents |
|---|---|
| `breach_report_items.csv` | One row per report, ISIN and covenant cell: dates as printed and as parsed, levels, actions |
| `breach_notices.csv` | Trustee notices: trust deed dates, dates of intimation, meetings, quorum |
| `provisions.csv` | Contract clauses with parsed limits, including earlier and amended versions |
| `instrument_status.csv` | What the reviewed record says, per ISIN and period, and on what basis |
| `notice_report_comparisons.csv` | A trustee's report compared mechanically with its own notice |
| `evidence.csv` | Every anchor: document, page and quotation |
| `documents.csv` | Every cited file with its URL, SHA-256 and dates |
| `discrepancies.csv`, `searches.csv`, `sources.csv` | Open disagreements, the search log and the access policy per source |

Statuses come from a closed list, and they must never be merged. [docs/data-model.md](docs/data-model.md) defines them.

| Status | Meaning |
|---|---|
| `reported_breach` | A trustee report, notice or statement says so |
| `reported_no_breach` | An explicit statement covers this instrument and period |
| `no_information_reported` | The reporting party says it received no information |
| `no_report_found` | The reviewed sources do not list the instrument. **Not** a sign of compliance |
| `inaccessible` | A relevant disclosure could not be reached |
| `ambiguous` | The sources cannot settle it, for example because the trustee is disputed |
| `conflicting` | Sources or versions disagree |
| `not_assessed` | Nobody has looked yet |

Rows derived from a source that reserves AI-training rights carry `ai_training_reserved = true`.

## Reproducing it

Requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/).

```console
$ uv sync
$ uv run brdo validate              # schema and cross-record checks, offline
$ uv run pytest                     # test suite, offline
$ uv run brdo fetch                 # download the cited files into a local cache, checking hashes
$ uv run brdo verify                # re-test every evidence anchor against those files
$ uv run brdo build --sqlite dist/brdo.sqlite
$ uv run brdo report --out docs/observability-report.md
```

`brdo verify` reports how each passage was matched and lists any page whose text layer cannot be trusted. Exports are deterministic, and the tests fail if the committed exports or report drift from the records. A file that has changed at its source shows up as a hash mismatch and is never silently accepted.

Source documents are not in this repository. See [docs/source-policy.md](docs/source-policy.md).

## Repository layout

```
data/       The records: the source of truth, validated by schema and checked against the sources
exports/    Flat CSV files generated from data/
schema/     JSON Schemas for each record type
src/brdo/   Loading, retrieval policy, evidence checking, status derivation, exports, report
tests/      Offline tests, including checks on the published dataset itself
docs/       Research design, landscape, source policy, data model, methods, generated report
```

## Limits of this release

- **The contract itself is not in the evidence yet.** Clauses are quoted by trustees, issuers and a rating agency, and the provisions file says which. No trust deed or offer document has been retrieved; the candidates are [listed](docs/observability-report.md#candidates-awaiting-manual-retrieval) for manual ingest.
- **The sample is selected on reported breaches.** It says nothing about how common breaches are.
- **One quarter, six trustees.** NSE-only material is excluded, and two trustees' reports were not located. Bond Central could not be reached for review.
- **Single-pass curation.** Transcriptions and annotations have not had an independent second review (`annotation_reviewed` is false throughout). The machine checks catch transcription errors in quotations; they cannot catch a wrong classification.
- **Quotations are deliberately short.** Trustee text is capped at 160 characters, so the source page must be opened to read a long clause in full.

## Roadmap

1. Ingest the located contract documents, then compare each clause as reported with the clause as written.
2. Add earlier quarters to measure persistence and revisions, and capture each new version of a report as it appears.
3. Add a sample of instruments with no reported breach, to make observability comparable across instruments.
4. Seek permission from exchanges and trustees for automated access and fuller quotation.
5. Build a source-grounded benchmark for clause retrieval and breach classification, excluding sources that reserve AI-training rights.

## Licence

Code is under the [MIT Licence](LICENSE). The curated records are under [CC BY 4.0, with carve-outs](LICENSE-DATA.md): quotations remain their owners' and source documents are not included. Corrections and takedown requests are welcome as [issues](https://github.com/itzsam-lol/bondholder-rights-observatory/issues).

This project is independent. It has no affiliation with or endorsement from SEBI, any exchange, depository, debenture trustee, rating agency or issuer, and it does not claim to be complete.
