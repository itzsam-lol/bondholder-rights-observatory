# Reliability, and the annotation guide

How far each kind of value in the records can be relied on, what was checked, what was found wrong, and the rules a second annotator should apply. Written on 4 November 2026.

## In brief

- **Quotations and parsed facts are checked by machine** against the hashed source files. At the last full run of `brdo verify`, on 4 November 2026, 1,147 of 1,254 anchors were found in the file's text layer and 107 rest on reading the rendered page. That run could not be repeated in this pass: the sources were unreachable from the environment used, so the figure is carried forward, not re-measured.
- **Classifications are one curator's reading.** None has had an independent second review. `annotation_reviewed` is false throughout, and the data dictionary marks every such column as `annotation`.
- **Mechanical comparisons are reproducible, which is not the same as correct.** Checking each decision against the quoted text found two rule errors in this pass (below).
- **The headline findings rest on few judgements about few issuers.** They are listed below, so that a reviewer can check every one in an afternoon.

## Kinds of value, and how each is checked

| Kind (data dictionary) | Checked by | Cannot catch |
|---|---|---|
| `source_text` | `brdo verify`: the words must occur on the cited page of the hashed file | Words read from an image when the text layer lacks them (`read_from_rendering`); a quotation from the wrong row of a table |
| `read_from_source` | Dates must match their printed text; ISINs pass their check digit; deed and intimation dates must be printed in their quotations; `brdo verify` checks levels | A consistent misreading, such as the wrong row's date |
| `annotation` | Schema and closed vocabularies only | Any wrong judgement |
| `derived` | Tests on the rules; committed exports must equal the code's output | A rule that does not mean what its name says |
| `provenance` | Hashes, the source policy in code, and tests that no excluded source is cited or linked | Whether a source's policy was read correctly |

## What this pass checked, and what it found

1. **Field-level comparison.** All 85 decisions behind the table of what each party adds were checked against the quoted text. One was wrong. The clause-reference rule read the decimal in the measured level "-1.02%" printed for INE179P07589 as a numbered clause. The rule now needs a named reference, or a numbered paragraph opening the text. "Clause reference: printed only by the trustee" falls from 10 to 9, and "neither" rises from 1 to 2. Tests pin both the error and correct references. Every decision is now exported with the text that satisfied its rule (`field_flows.csv`).
2. **Follow-up states.** A letter about the quarter ended 31 March 2026 (`idbi-notice-pvp-2026-06-p1`) was counted as follow-up of the June 2026 quarter. That gave two ISINs a "meeting reported as scheduled" state from another quarter's letter, and IDBI's count falls from 22 to 20. Letters that name another quarter are no longer counted; letters continuing an adjourned meeting name no quarter and still count. Every state is now exported with the row or letter that shows it (`follow_up_states.csv`).
3. **Cures.** The four IDBI rows behind "24 cures, none of a financial covenant" were read against their quoted cells. Each names a non-submission, such as "Non submission of financial results", and says the breach was cured. The finding holds. Its 24 ISINs belong to three issuers, 23 of them to two public bodies.
4. **Point-in-time views.** Claims, observations and issuer name variants supported only by later documents leaked into views of earlier dates. A report not yet public was labelled "not searched". Both are fixed, and a test now checks the view at every date on which some document's availability changes.
5. **Availability dates.** 44 server Last-Modified headers were recorded as publication dates. They are now recorded as what they are.

The audit re-applied the stated rules and read the quoted text. It is not an independent second annotation and must not be counted as one.

## What the headline findings rest on

| Finding | Judgements it rests on | About how many | Robustness |
|---|---|---|---|
| No cure of a financial covenant is published | `cure_reported` action labels and the covenant categories of 4 IDBI rows | 8 | Strong: the cells say so in words. Narrow: 3 issuers |
| No outcome is published for Catalyst's 44 ISINs | Action labels of Catalyst's rows, and adjournment flags of its letters | 30 | Strong: every action cell reads "Awaiting instructions from Debenture Holders" |
| Issuer and trustee: 17 agree, 3 differ, 2 not comparable | `made_by`, `scope` and `breach_stated` of 4 statements; the category of the governance item in Catalyst's row 5, which decides "not comparable" for Infinity's management statement | 13 | Scope is as printed; one category call decides two outcomes |
| What each party adds | The `clause_text` specificity of 22 trustee items, which gates "obligation wording", and three text rules | 22 plus rules | Moderate: one rule error found and fixed; the specificity gate is a judgement |
| How much of the contract each report prints | Specificity of all 73 covenant cells | 73 | The weakest; see the hard cases below |
| Trace to the contract | Specificity, and 18 links between cells and clause records | 90 | Moderate |
| Status per ISIN and period | Mechanical, given `period_end` on 51 letters and one `carried_over_from` | 52 | Strong where a letter states its quarter; check the rest |

Checking the first four rows, about 75 decisions, would cover every judgement behind the fourth pass's main findings.

## Annotation guide

These are the rules the existing annotations follow, written down so that a second annotator can apply them independently. A hard case is one where a careful reader could reasonably choose otherwise. Hard cases should be annotated twice and adjudicated, never silently relabelled.

### Covenant category (`BreachItem.category`, `Provision.category`)

The categories of SEBI's guidance note, Annex-VIA of the master circular: accounts, funds and reserves; financial; affirmative; credit rating; negative; default. Anything outside them is `other`.

- **Financial:** a ratio or amount the issuer must keep within a limit, such as portfolio at risk, capital adequacy, debt to equity or return on assets.
- **Other:** information and filing undertakings, such as "Non submission of financial results"; insolvency events; post-closing deliverables. Also a clause cited by number with no words, with a note.
- **Hard cases.** Security cover is labelled `affirmative` throughout ("Non-Maintainance of Security cover", Catalyst's row 6), though it is a ratio. That is defensible only if applied consistently, and it matters wherever a statement covers financial covenants only. "Delay in Listed" (Vistra) is labelled `default`.

### Specificity (`BreachItem.specificity`)

Judged on the whole printed cell, not only the quoted part.

- `clause_text`: the undertaking in words, with any threshold, for example "(e) a Write-Off Ratio may not at any time increase above 6.5%".
- `requirement_and_actual`: both the required and the achieved level, for example IDBI's ROA and DSCR rows.
- `clause_number_only`: a reference with no words.
- `description_only`: names or paraphrases the failure without stating the term.
- **Hard cases.**
  - IDBI's row 1 begins "The maximum permissible ratio of the sum of PAR > 30 and write-offs ...". It quotes a ratio's definition inside a description of the failure, and is labelled `description_only`.
  - Axis's row names "Total Financial Indebtness:Tangible Net worth" without a level, and is labelled `description_only`.

  Both deserve a second reading.

### Actions (`BreachRow.actions`)

One or more kinds per row, read from the action columns only.

- `cure_reported` needs the cell to say that the breach was cured or the missing item supplied.
- A meeting is `holders_meeting_held` if the cell reports it as held, and `holders_meeting_scheduled` if a date lies ahead.
- `awaiting_instructions` and `follow_up_with_issuer` follow the cell's words.
- Mixed cells take every kind they report; Vistra's row 1 has three.

### Other fields

- **Assignment** (`assignment_uncertain`): true only when which row an ISIN belongs to depends on reading merged cells. False throughout this release.
- **Carried over** (`carried_over_from`): set only when the row's own label assigns the breach to an earlier quarter.
- **Letters** (`BreachNotice.kind`, `period_end`): `period_end` is set when the letter states the quarter or the certificate's period. Continuation letters have none.
- **Statements**:
  - `made_by` is whoever signs the conclusion: the issuer, or its statutory auditor;
  - `scope` is as printed;
  - `breach_stated` is true when the statement lists exceptions or says a covenant was not met;
  - `isins_printed` is false when an ISIN is reached only by a general sentence or by omission from a list of exceptions.
- **Clause records**:
  - `stage` follows the document: a party's quotation is `described_in_force`, an exchange's approval `approved_in_principle`, and only the executed instrument `executed_text`;
  - `thresholds` are parsed only where the comparator, value, unit and dates are unambiguous;
  - `explanation` is written from the quoted text alone.
- **Search outcomes** (`SearchRecord.outcome`):
  - `found` only with a registered document;
  - `located_not_retrieved` when a candidate sits on a source the pipeline may not use;
  - `excluded_by_policy` when it sits only on an excluded source;
  - `access_error` when a source failed to answer, including a robots file that could not be read.

## Making the annotations dependable

1. **Fix the guide as the codebook** for a review round, and record its commit.
2. **Annotate a second time, blind to the current values,** with someone who did not make them. Start with the roughly 75 judgements behind the main findings, then do every covenant category and specificity.
3. **Measure agreement field by field.** Report raw agreement and Cohen's kappa with their counts, and never pool fields.
4. **Adjudicate and keep both readings.** Record the first and second values and the adjudicated one, and say why. Set `annotation_reviewed` only on reviewed records.
5. **Regenerate the report** and record in the changelog every finding that moved.
6. **Keep hand-checked decisions as tests** for every mechanical rule, as this pass did for the clause-reference rule.

None of these is review: the same curator re-reading, the same process re-applying the same rules, or two publications that share an origin agreeing with each other.
