# Bondholder Rights & Disclosure Observatory

An independent, evidence-backed record of what Indian listed corporate bonds promise, and of what later becomes publicly known about those promises.

A bond's protections sit in a trust deed. What happens to them afterwards is scattered across trustee websites, issuers' own filings, exchange approvals and rating rationales. This project connects them at the level of the individual ISIN:

```
Issuer → ISIN → Trust deeds and amendments → Clause → Trustee's report, issuer's statement → Reported action → Original page
```

Every statement in the dataset says who made it and points to a hashed file, a page and the words relied on. A checker re-tests all of those pointers against the source files, so the record can be audited rather than trusted.

> **This is not investment advice, and it makes no finding about anyone's compliance.** A record that a trustee reported a breach means exactly that: the trustee reported it. The absence of a report is not evidence that no breach occurred.

## An example

```console
$ brdo show INE00VD07016          # output shortened
INE00VD07016  Infinity Fincorp Solutions Private Limited
  claim  debenture_trustee: catalyst-trusteeship  (asserted by catalyst-trusteeship)
  report ctl-t5-2026-06 row 5: (i) comply with any corporate governance requirements applicable to the Company ...
  notice ctl-notice-infinity-2026-08 p6 2026-08-14 [breach]; deeds: 2024-09-30
  stated infinity-sc-2026-08-07 2026-06-30 by statutory_auditor (all_covenants): compliance
  stated infinity-sc-2026-08-07 2026-06-30 by issuer (financial_covenants): compliance
  open   infinity-governance-covenant: The trustee's June 2026 quarter report lists both ISINs for a breach ...
  status 2026-06-30: conflicting (statements_disagree)
```

Here the trustee reports a breach of a governance undertaking as at 30 June 2026. The issuer's auditor, six days before the trustee says it detected the breach, gave limited assurance that nothing suggested non-compliance with all covenants at that date. The issuer's own confirmation covers financial covenants only, so it is recorded as not addressing the governance undertaking. The dataset keeps both statements and the disagreement between them. It does not pick a winner.

`brdo show INE179P08082` shows the other kind of case: five public statements of one cost-to-income covenant, most of which are explained by an amendment approved in principle by the exchange. It also shows two statements that the amendment does not explain.

## What this release contains

The sample starts from the quarterly covenant-breach reports that SEBI requires debenture trustees to publish (Annex-VIIA, Table 5), for the quarter ended 30 June 2026.

| | |
|---|---|
| Trustees with a logged search | 8; a report was found for 6 |
| Breach reports transcribed | 8 files, including two versions of one quarter and one later as-of report |
| Instruments | 96 ISINs of 29 issuers; 93 are listed in a trustee report |
| Trustee notices and letters | 66 records from 23 files, giving trust deed dates and clause references |
| Issuers' and auditors' statements | 6 statements of covenant compliance in 4 filings, with 40 exception lines |
| Amendment trail | 1 issuer intimation under regulation 59 with the exchange's in-principle approval |
| Trustee census | 1 table of the issues a trustee monitors: 1,832 ISINs, measured rather than republished, with a reproducible sample of 20 |
| Contract clauses | 25, with parsed limits where the wording is unambiguous and plain-English notes |
| Search log | 69 attempts, successful or not |
| Open discrepancies | 18 |
| Evidence anchors | 1,254. At the last full run of `brdo verify` (4 November 2026), 1,147 were verified by machine against the file's text and 107 read from the rendered page |

The full, generated measurements are in the [observability report](docs/observability-report.md).

## What the record shows so far

These describe this sample, which is selected on a breach having been reported. They do not describe the market.

- **Counts of ISINs overstate the evidence.** One issuer's ISINs usually share one deed, one certificate and one letter. Five issuers hold 48 of the 91 ISINs listed for the quarter, and the field-level findings below rest on two issuers. The report prints the number of issuers beside every count of ISINs. See [docs/coverage.md](docs/coverage.md).

- **The trace to the contract breaks at the last step, and for access reasons.** Trustees' letters cite a dated trust deed or trustee agreement for 52 of the 93 listed ISINs. No offer document or deed could be retrieved through the pipeline. BSE refuses identified automated clients, NSE is excluded under the project's policy (a re-reading of its terms on 5 November 2026 could neither confirm nor relax it), and a bond platform's terms forbid extraction tools.
- **The issuer publishes too, but its statement is upstream of the trustee's report, not independent of it.** Issuers must give their trustee an auditor-certified statement of covenant compliance every quarter and keep it on their website. Logged searches for the June 2026 quarter found one for 3 of 11 issuers, and one more was refused to the project's client. By two trustees' own printed definitions, the dates in their breach reports are the certificate's dates.
- **Agreement is mostly transmission; divergence is where new information shows.** Of 22 comparisons, for 20 ISINs of 3 issuers, 17 agree, 3 differ and 2 cannot be compared. The 17 agreements come from 2 issuers. In every agreement the trustee dates its detection on or after the issuer's material reached it, and in 6 it cites the auditor's certificate. Agreement shows the statement was carried through, not that it was confirmed. The differences show information that one party has and the other lacks: an auditor's all-covenant conclusion against a trustee's governance breach, and an issuer's breach the trustee does not list.
- **Agreement within one trustee proves even less.** Wherever a trustee's notice prints a level (24 comparisons), it matches that trustee's report.
- **Contract versions leave public traces even when contracts do not, but traces are not the contract.** Changing the terms of listed debentures needs the exchange's prior approval, after the board, the trustee and three-fourths of holders agree. One issuer's intimation of that approval explains most of five differing statements of one covenant, yet cannot settle which limit applied on the test date. Every clause record says whether it is a party's description, an offer document's text, a proposal, an approval in principle or executed text. These are different legal stages. None yet is from an offer document or a deed.
- **A trustee's own census gives a denominator.** Catalyst's table of compliance reports received for the quarter prints 1,832 ISINs; its breach report lists 44 of them (2.4%). A listing is not a breach rate.
- **The published follow-up mostly stops before an outcome.** No trustee publishes a cure of a financial covenant; the 24 cures published, for ISINs of three issuers, are late filings and similar obligations made good. For every ISIN Catalyst listed, no outcome is published at all.
- **Each party adds what it alone holds.** Where issuer and trustee agree on a breach, the trustee adds the deed's wording, references and dates; the issuer adds the measured level, which the trustee repeats in one of nine cases. The agreements come from two issuers, and the measured-level contrast from one, so this is a well-documented case rather than a pattern.
- **Trustees differ in what they publish as a breach.** Catalyst's census marks the compliance report as not received for 59 ISINs, of which its breach report lists 2; IDBI's report lists non-submission of results as breaches.
- **What was public when can be bounded, not proved.** Every document carries a lower bound, an estimate and the day the project observed it. `--as-of` rebuilds the record as it stood on a date: an instrument, an issuer's name or an identifier appears only once a record then public prints it, and later notes and searches are left out. Views built from the estimates and from the project's observations are kept apart. Tests show that the views agree with the recorded dates, not that those dates are true. By the servers' Last-Modified dates, the issuers' statements preceded the trustees' reports in every comparison. The project's own observations, all from 3 and 4 November 2026, cannot order them.
- **Trustees' disclosures carry very different amounts of the contract.** One trustee prints the clause text for nearly every ISIN. Others mostly print a description such as "Non submission of financial results".
- **The same column means different things.** "Date of actual breach" is defined differently by different trustees, and used in two ways within a single report. An issuer's statement date confirms one trustee's printed definition.
- **Disclosures change without notice.** Only a reader who kept both versions of one report can see that a "seeking instructions" became a reported waiver.
- **Text extraction alone misreads these documents.** One report draws most of its text as vector outlines, and several issuer annexures are scans. The pipeline detects both, and a report cannot be marked complete unless its rendered pages were reviewed.

The research question, method and threats to validity are in [docs/research-design.md](docs/research-design.md). Where the project should go next, and why, is in [docs/research-agenda.md](docs/research-agenda.md).

## Using the data

Flat files are in [`exports/`](exports), and the records they are built from are in [`data/`](data).

| File | Contents |
|---|---|
| `breach_report_items.csv` | One row per report, ISIN and covenant cell: dates as printed and as parsed, levels, actions |
| `breach_notices.csv` | Trustee notices: trust deed dates, dates of intimation, meetings, quorum |
| `compliance_statements.csv`, `compliance_statement_exceptions.csv` | Issuers' and auditors' statements, who made them, what they cover, and each exception line |
| `statement_report_comparisons.csv` | Each statement set beside the trustee's report for the same quarter |
| `provisions.csv` | Contract clauses with parsed limits, including earlier and amended versions |
| `instrument_status.csv` | What the reviewed record says, per ISIN and period, and on what basis |
| `notice_report_comparisons.csv` | A trustee's report compared mechanically with its own notice |
| `field_flows.csv` | For each issuer–trustee agreement, which party prints each kind of information, and the text behind each decision |
| `follow_up_states.csv` | Every follow-up state published for each listed ISIN, with the report row or letter that shows it, and how its quarter is known |
| `attribute_support.csv` | For each instrument, issuer, name and identifier, every record that supports it and when that record became public: what `--as-of` views rely on |
| `instruments.csv`, `issuers.csv` | The entities, with linked offer documents and executed deeds kept apart, and when each was first established by a public record |
| `evidence.csv` | Every anchor: document, page, quotation, and whether it was read from the rendered page |
| `documents.csv` | Every cited file with its URL, SHA-256, how it was retrieved, and its lower bound, estimate and observation of availability |
| `discrepancies.csv`, `searches.csv`, `sources.csv` | Open disagreements, the search log and the access policy per source |

Every column is described in [docs/data-dictionary.md](docs/data-dictionary.md), and in `exports/datapackage.json` (a [Frictionless Data Package](https://datapackage.org/) descriptor) for tools outside this repository. Each column is labelled with one kind:

- `source_text`: a quotation, not covered by the licence;
- `read_from_source`: a fact the source states;
- `annotation`: the project's single-pass reading;
- `derived`: computed by code;
- `provenance` or `identifier`.

Where a fact originates with someone other than the party publishing it, the dictionary says so.

Statuses come from a closed list, and they must never be merged. [docs/data-model.md](docs/data-model.md) defines them.

| Status | Meaning |
|---|---|
| `reported_breach` | A trustee report, notice or explicit statement says so |
| `reported_no_breach` | An explicit statement covers this instrument and period, and nothing disagrees |
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
$ uv run brdo dictionary            # the data dictionary, after checking every column is described
$ uvx --from 'frictionless==5.18.1' frictionless validate exports/datapackage.json   # an independent check of the package
$ uv run brdo show INE179P08082 --as-of 2026-08-15   # the record as it stood on a date, by estimated availability
$ uv run brdo status --as-of 2026-11-03 --availability observed   # only what the project itself saw by then
$ uv run brdo review packet --out ../review-round-1   # a blind packet for a second annotator, and its key apart
```

`brdo fetch`, `brdo verify` and `pytest -m network` need a network that reaches the sources; everything else runs offline. In a view of an earlier date an issuer's name may be blank, as Dvara's is on 15 August 2026: a name counts only where a record then public is transcribed as printing it.

`brdo verify` reports how each passage was matched and lists any page whose text layer cannot be trusted. Exports are deterministic, and the tests fail if the committed exports or report drift from the records. A file that has changed at its source shows up as a hash mismatch and is never silently accepted.

Source documents are not in this repository. See [docs/source-policy.md](docs/source-policy.md).

## Repository layout

```
data/       The records: the source of truth, validated by schema and checked against the sources
exports/    Flat CSV files generated from data/
schema/     JSON Schemas for each record type
src/brdo/   Loading, retrieval policy, evidence checking, status derivation, comparisons, exports, report
tests/      Offline tests, including checks on the published dataset itself
docs/       Data model and dictionary, methods, reliability, coverage, source policy, exchange access,
            legal review brief, research design and agenda, landscape, generated report
```

## Limits of this release

- **The contract itself is not in the evidence yet.** Clauses are quoted by trustees, issuers, an exchange's approval letter and a rating agency, and the provisions file says which. No trust deed or offer document has been retrieved, and the two are different legal stages: an offer document shows the terms as offered, not as executed. The candidates are [listed](docs/observability-report.md#candidates-awaiting-manual-retrieval) for manual ingest.
- **The sample is selected on reported breaches.** It says nothing about how common breaches are.
- **One quarter, six trustees, three issuers' own statements.** NSE-only material is excluded, two trustees' reports were not located, and Bond Central's per-ISIN pages and terms have not been read. Issuer statements were mostly sought through a search engine, which misses filings that are on issuers' sites.
- **Issuers' statements are self-reports.** Auditors give them limited assurance, not an audit opinion, and a statement limited to financial covenants says nothing about other undertakings.
- **Single-pass curation.** Transcriptions and annotations have not had an independent second review (`annotation_reviewed` is false throughout). The machine checks catch transcription errors in quotations. They cannot catch a wrong classification. [docs/reliability.md](docs/reliability.md) lists the judgements each finding rests on, the errors found in two audits of the mechanical rules and views, and the protocol for a blind second annotation, whose rules are in [docs/annotation-codebook.md](docs/annotation-codebook.md).
- **Availability dates before November 2026 are estimates.** They rest on servers' Last-Modified headers, which date the file version held. The project observed every file on 3 or 4 November 2026.
- **Quotations are deliberately short.** Text from sources with restrictive terms is capped at 160 characters, so the source page must be opened to read a long clause in full.

## Roadmap

The dataset is the product, so the order puts trustworthiness before size. [docs/research-agenda.md](docs/research-agenda.md) explains what the research questions ask of the data, and the documents linked below what is pending.

1. **Independent second annotation** of the judgements behind the main findings, by a person, from the packet `brdo review packet` writes, with agreement measured per field and every disagreement kept ([docs/reliability.md](docs/reliability.md#review-protocol)).
2. **Re-run `brdo verify`** from a network that reaches the sources, and commit a dated record of which anchors verified.
3. **Close the cheapest gaps by hand:** Pahal's two filings and the BSE candidates, under the manual-only policy ([docs/coverage.md](docs/coverage.md)).
4. **Assess Bond Central** in a browser. Then decide, with the legal questions answered, whether to ask the exchanges about research access ([docs/exchange-access.md](docs/exchange-access.md), [docs/legal-review-brief.md](docs/legal-review-brief.md)).
5. **Capture every disclosure page each quarter,** so that availability is observed rather than estimated, and revisions and removals can be measured.
6. **Widen the sample** only after these: every sample issuer's regulation 62 page over several quarters, covenant versions from amendment trails, a comparison sample from trustees' censuses, and further trustees, with a note on how each trustee uses the columns of the prescribed breach report.
7. Later, and only after independent double annotation, build an evaluation set for document understanding that excludes sources reserving AI-training rights.

## Licence

Code is under the [MIT Licence](LICENSE). The curated records are under [CC BY 4.0, with carve-outs](LICENSE-DATA.md). Quotations, document titles and trade names remain their owners' wherever they appear, including in code, tests and documentation, and neither licence covers them. Source documents are not included. Corrections and takedown requests are welcome as [issues](https://github.com/itzsam-lol/bondholder-rights-observatory/issues).

This project is independent. It has no affiliation with or endorsement from SEBI, any exchange, depository, debenture trustee, rating agency or issuer, and it does not claim to be complete.
