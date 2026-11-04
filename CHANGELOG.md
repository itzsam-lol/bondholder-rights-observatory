# Changes

Changes to the records, the exports and the figures derived from them. Corrections to figures published earlier are listed first, with the old and new values, so that anyone who cited a figure can see what changed and why. The repository's history holds every earlier state.

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
