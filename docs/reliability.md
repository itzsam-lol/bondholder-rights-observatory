# Reliability, and the annotation guide

How far each kind of value in the records can be relied on, what was checked, what was found wrong, and the rules a second annotator should apply. Written on 4 November 2026, and revised on 5 November 2026 after two audits: of the fifth pass's rules and views, and of the attribute supports and historical views that audit introduced.

## In brief

- **Quotations and parsed facts are checked by machine** against the hashed source files. At the last full run of `brdo verify`, on 4 November 2026, 1,147 of 1,254 anchors were found in the file's text layer and 107 rest on reading the rendered page. That run could not be repeated on 4 or 5 November: the sources were unreachable from the environment used, so the figure is carried forward, not re-measured. Separately, 246 anchors are recorded as transcribed from the rendered page (`read_from_rendering` in `evidence.csv`). That is a fact about how they were transcribed, not a verification result: `brdo verify` reports an anchor as `visual_only` only if it is one of those 246 and its words are not in the text layer, which at that run was true of 107. See [verification-runbook.md](verification-runbook.md).
- **Classifications are one curator's reading.** None has had an independent second review. `annotation_reviewed` is false throughout, no review record exists, and the data dictionary marks every such column as `annotation`.
- **Mechanical comparisons are reproducible, which is not the same as correct.** Checking each decision against the quoted text found two rule errors on 4 November, and an audit of that work on 5 November found further errors in the rules and views (below).
- **The headline findings rest on few judgements about few issuers.** They are listed below, so that a reviewer can check every one in an afternoon.
- **Historical views now say what they rest on.** Each admitted file is `confirmed` or only `uncertain` on the view's day, and no file was confirmed before 3 November 2026. An entity or attribute appears only with a support whose basis is named; 79 of the 630 supports are recorded but establish nothing (below).
- **Materials for a blind second annotation are ready, but none has been made.** `brdo review packet` writes the 585 decisions without their current values, in two rounds; [annotation-codebook.md](annotation-codebook.md) states the rules; the protocol is below.

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

## What the audit of that work found, 5 November 2026

The fifth pass's own changes were re-examined. These were wrong or incomplete, and are corrected:

1. **Point-in-time views still leaked.** They kept every instrument and issuer, with its base name, CIN, LEI and sector, whatever the date, and kept notes and searches written later. They also carried a list of what they withheld, which itself tells what the full record holds. Now an entity or attribute appears only when a record then public supports it (`attribute_support.csv`), notes and later searches are dropped, and no such list exists.
2. **"Not yet public" was not justified.** A view labelled a report `trustee_report_not_yet_public` because a later search found it. A later search cannot show that the report was not public earlier. The label is gone; an estimated view says only that it holds no such report (`trustee_report_not_in_view`).
3. **A continuation letter counted for every quarter.** A letter continuing an adjourned meeting states no quarter, and was attached to whichever quarter was asked about. It is now tied to a quarter only by a stated rule, and otherwise to none. Catalyst's counts fall from 15 to 14 ISINs for "meeting adjourned for lack of quorum" and from 39 to 38 for "meeting reported as scheduled": the continuation letter for INE179P07530 cannot be tied to a quarter.
4. **A cure was typed by any one covenant of its row.** It is now typed only when every covenant the row lists for the ISIN is of one kind. No figure changed, because no row mixes kinds.
5. **Field flows kept only the first supporting line.** They now keep every line, with the number examined; 22 of the 85 decisions rest on more than one. The clause-reference rule was tightened and pinned by 30 hand-written cases (12 that count and 18 that do not), including the decimals, headings, statutes and dates that could mislead it. No figure changed.
6. **Offer documents were treated as the contract.** The vocabulary called text from an offer document "executed", and the trace to the contract counted offer documents as the contract itself. They are now separate stages, checked by validation (see [data-model.md](data-model.md#clause-records-and-their-legal-stage)). No record was affected.
7. **The fetcher still fetched when a robots file could not be read.** A 403, 429 or other refusal at the robots address, or an HTML page in place of the file, was treated as no robots file. Now only a robots file, or a 404 or 410, settles the policy. One document in the dataset, ICRA's rationale `icra-krcl-139196`, was retrieved by the pipeline on 4 November 2026, while ICRA's robots address returned a bot-mitigation page; under the corrected rule it would not have been fetched. The record is kept as it was. Whether to re-retrieve it by hand is for the project owner.


## What the audit of attribute support found, 5 November 2026

Every one of the 521 support rows the previous audit exported was checked against the anchors, observations and records behind it. Source files could not be reopened, because none was cached and the hosts were unreachable, so a row was judged on whether the record's own quotation or observation prints the value, not on the file itself.

| Attribute | Rows | What they rested on | Verdict |
|---|---|---|---|
| Instrument identity (the ISIN) | 321 | 315 quotations printing the ISIN, 2 ISIN lists recomputable from the census file, 2 depository pages whose address names the ISIN, 2 a curated `isins_printed` flag with no quotation | Sound except the 2 flag-only rows, now labelled `flag_only` and not relied on |
| Issuer identity, which also carried the ISIN-to-issuer link | 153 | 37 breach rows printing the name beside the ISINs, 4 name variants, 4 depository pages showing the name, 4 the issuer's own filings, 33 records whose quotation did not print the name though another anchor of the same file did, and 71 records with no transcribed evidence of the issuer at all: 63 trustee letters, 4 census rows, 2 claims and 2 depository observations of the trustee | Too permissive. A record printing an ISIN does not show whose it is |
| Issuer name | 40 | 37 exact, 3 the name plus a parenthesis ("(NHAI)", "(formerly known as …)") | Sound, but matched by substring. Two issuers share the name "Samunnati Finance Private Limited", so the name told neither apart, and their identifiers encode CINs seen only on 3 November |
| CIN and LEI | 7 | 1 the issuer's own filing, 6 depository pages for the issuer's ISINs (2 duplicates) | Sound |

**Corrections.**

1. Which issuer an ISIN belongs to is now its own attribute (`instrument`, `issuer`), with bases: `printed_with_name`, `issuer_publication` (using a new, explicit link from each issuer's website to the issuer), `observed`, and `issuer_code` for inference from a code no other issuer uses. A trustee's letter printing only the ISIN is kept as `letter_to_holders` but establishes nothing.
2. An issuer's identity needs its name, a variant, its CIN or LEI, or its own website. It no longer follows from any record printing one of its ISINs.
3. Names match as whole names, exactly or with a parenthetical addition, never by containment. Issuers whose name another issuer shares are not told apart without an identifier or their own website.
4. A claim's or link's evidence establishes an ISIN only where its quotation prints it, and a depository page only where its address or value names it.
5. A view refers to an issuer it cannot identify, or cannot tell from another, by its ISINs' issuer code, never by the dataset's identifier.

**What the corrected rules give.** 630 support rows, of which 551 establish their attribute; with 86 issuer-code inferences, `attribute_support.csv` has 716 rows. By the end of the record every one of the 96 instruments and 29 issuers is reconstructed, and every issuer link is established: 93 by a record printing the issuer's name with the ISIN, 2 by the issuer's own publication and 1 by issuer-code inference. Earlier views differ. 33 ISINs appear before their issuer link does, typically printed in an August trustee letter and named in a September report. Dvara's, Infinity's and Satya's own filings identify them before any admitted record prints their names. No ISIN or link rests on the census alone: its rows print ISINs but no names.

**What this audit could not do.** It could not reopen any file, so a quotation that misrepresents its page would not have been caught here. That is what `brdo verify` is for, and it has not run since 4 November.

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

## The rules, and the hard cases as currently annotated

The rules a second annotator applies are in [annotation-codebook.md](annotation-codebook.md). The codebook states rules only: a second annotator must not see what follows until their answers are in, because it says how the hard cases are labelled now. It is kept here for adjudication.

A hard case is one where a careful reader could reasonably choose otherwise. `brdo review packet` flags 23 decisions as hard from the text alone, without looking at their values, and its notes never suggest a value. Hard cases should be annotated twice and adjudicated, never silently relabelled.

- **Security cover.** Every cell about maintaining security cover is labelled `affirmative`, including Catalyst's "Security Cover Ratio - 1.10x" (row 6) and Vistra's "Non-Maintainance of Security cover", although security cover is a ratio kept within a limit, the codebook's gloss for `financial`. SEBI's annex lists "Security Cover as per terms of Issue" under its third heading, "Affirmative", so the labels follow it. This was read on 5 November 2026 from a third-party copy of the master circular of 28 September 2026 and from copies of the circular of 19 May 2022 that introduced the annex, not from the project's hashed copy, which was not in the local cache. It matters wherever a statement covers financial covenants only, because such a statement does not reach a security cover breach.
- **Ratios without a level.** IDBI's row 1 ("The maximum permissible ratio of the sum of PAR > 30 and write-offs ...") and Axis's row 1 ("Total Financial Indebtness:Tangible Net worth") are labelled `description_only`: each names or defines a ratio but states no limit. IDBI's row 3 (DSCR) is labelled `requirement_and_actual`, though its levels are bare numbers, which `levels_stated` does not record.
- **Payment.** MITCON's "Non Payment of Interest & principal" is labelled `default`. The annex lists "Payment of Interest on due dates" under "Financial" and "Default of principal or interest or both" under "Default", so either can be argued.
- **A class of covenants named, the undertaking not.** IDBI's row 10 cites "clause 1.4.1(vi) of Negative Covenants" and is labelled `negative`. The written rule, that a clause cited only by number is `other`, would give `other`. With Vistra's listing delay below, it is one of two labels found that may not follow the written rules. It is left unchanged for adjudication.
- **Governance.** Catalyst's row 5 ("comply with any corporate governance requirements ...") is labelled `affirmative`. That one call decides whether Infinity's management statement, which covers financial covenants only, can be compared with the trustee's report.
- **Listing.** Vistra's "Delay in Listed" is labelled `default`. The annex's "Default" heading names defaults of payment and of security creation, not listing, so by the codebook it might be `other`. It is left unchanged for adjudication.

## Review protocol

1. **Choose the reviewer, and agree terms first.** The reviewer must be a person who did not make the original annotations and has not seen the data. Agree, before sending anything:
   - the label under which their answers will be recorded, and whether and how they wish to be credited;
   - that their answers may be released as part of the dataset under its licence (see [legal-review-brief.md](legal-review-brief.md) for the open question about this);
   - that they will not use AI tools or automated aids to decide, nor consult the project's data, exports, reports or repository until they have returned their answers;
   - how they will return `answers.csv`, and by when.
2. **Fix the codebook.** The codebook is committed as of `a8cd1e3`. If it is changed, commit it before generating a packet: `brdo review packet` records the codebook's commit in the packet's README, and warns if the codebook has uncommitted changes.
3. **Write the packet, outside the repository.** From the repository's root:

   ```bash
   uv run brdo review packet --out ~/brdo-review/round-1 --round 1
   ```

   Round 1 holds 356 decisions in 34 documents, 15 of them hard cases: every statement field, every row's actions, every letter's kind, quarter and adjournment, every covenant cell's category, and the specificity of the 23 cells listing an ISIN that a statement covers. They carry the statement comparisons, what each party adds, and the follow-up and cure findings. Round 1 would not validate the trace to the contract, the clause records and their legal stages, row assignment, carried-over quarters, or the specificity of the other 50 cells, which round 2's 229 decisions cover. The rounds are chosen by field and record, never by the current value.

   `packet/` holds `README.txt` (the round, counts, codebook commit and a table of the fields), `guide.md` (the reviewer's guide, [reviewer-guide.md](reviewer-guide.md)), `codebook.md`, `decisions.csv` (file, SHA-256, page, locator, ISINs, passage, allowed values, kind, rule, hard-case flag and note, and no current value) and a blank `answers.csv`. `key/` holds the current values, readable by its owner only. The command refuses to write inside the repository, so the key cannot be committed or published with the exports, and refuses to write over an earlier round. Packet ids are fresh for each round, because record ids could hint at a value.
4. **Check, then send `packet/` only.** Before sending, list the folder and confirm it holds exactly those five files, and that `decisions.csv` has no `value` column. Send the folder, for example as a zip, and keep `key/` where only you can read it. Never send the key, commit it, or put it in `exports/` or `docs/`.
5. **Annotate blind.** The reviewer works from the sources, following the guide. `none` is a value, for example a letter that states no quarter; a blank means the reviewer could not decide. Every hard case, every unsure answer, every blank and every reported problem needs a reason. A source that cannot be used is reported with a `problem` code: `source_unavailable`, `hash_mismatch`, `page_not_found` or `cannot_interpret`. A `hash_mismatch` means the publisher has changed the file; record it, and do not substitute another copy without legal advice.
6. **Score per field.** Keep the returned `answers.csv` beside the key, outside the repository, and run:

   ```bash
   uv run brdo review score --decisions ~/brdo-review/round-1/packet/decisions.csv --key ~/brdo-review/round-1/key/key.csv --answers ~/brdo-review/round-1/answers.csv > ~/brdo-review/round-1/scores.md
   ```

   The scores report each field separately, never pooled: counts, raw agreement, problems reported, both annotators' label distributions, every disagreement, every reported problem, and agreement on the hard cases and on the answers not marked unsure. How to read it:
   - **Categorical fields** get Cohen's kappa. Read it with the distributions: when one value dominates, kappa can be low although raw agreement is high, and with few decisions one disagreement moves it a lot.
   - **Binary fields** also get agreement on each value. For a rare value, such as `true` for row assignment, that number matters more than raw agreement, which is high even if the rare value is never agreed.
   - **Actions** are a set per row. Raw agreement is on the whole set, which is strict; mean Jaccard and per-label agreement show how close the sets are. No kappa is given.
   - **Dates** are compared exactly, and on whether a date is given at all. No kappa is given.
   - **Hard cases and unsure answers** are expected to disagree more. Report them, do not drop them.
7. **Adjudicate.** For each disagreement and each hard case, a person decides, with a reason, against the codebook and the source. The adjudicator may be the original curator, but must record that they are.
8. **Record every decision reviewed.** Add an `AnnotationReview` to `data/annotation-reviews.yaml` for each decision, with:
   - `decision`: the stable decision id, from the key;
   - `codebook_commit`;
   - `original` and `original_annotator`;
   - `second`, `second_annotator`, `second_by: person`, `second_unsure` and `second_reason`;
   - `annotated_on`;
   - and, where a disagreement or hard case was settled, `adjudicated`, `adjudicated_by`, `adjudication_reason` and `adjudicated_on`.

   Annotators are named by a label, not by any personal detail. Then change the record itself to the settled value. The review record keeps the original value, so adjudication never erases it.
9. **Mark only what was reviewed.** `Provision.annotation_reviewed` may be set only when reviews settle every decision of that clause record. Validation enforces this, and also rejects a review by the original annotator, a review that does not match the record, and a settled value the record does not hold. Other records' review state is read from the reviews themselves.
10. **Regenerate and log.** Rebuild the exports and the report, and record in the changelog every figure that moved.

**What is not a review.** The same curator re-reading; the same rules re-applied, including by these audits; another pass by an automated process or a language model, however it is prompted; and two publications with a shared origin agreeing with each other. `second_by` accepts only `person`, and there is deliberately no value for anything else. None of these may be recorded as an `AnnotationReview`, and none may set `annotation_reviewed`.
