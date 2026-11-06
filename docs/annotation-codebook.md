# Annotation codebook for a second annotator

This is the codebook for a label-blind second annotation of the project's judgements. It states the rules only. It does not say how any record is currently labelled, and an annotator should not look at `data/`, `exports/` or the reports until their answers are handed in.

Each line of a packet made by `brdo review packet` is one decision. It gives the document and page, a locator, the allowed values, a link to the rule below and, for a report's cell or a clause, the passage the record transcribes; letters and statements have no passage. The passage is a convenience: read the source itself, because the rules often depend on words around the quoted part. Record one value per decision, a short reason, and whether you are unsure.

A decision marked as a hard case is one where a careful reader could reasonably choose otherwise. Its note says what makes it hard, not what to choose. Apply the general rules, and say why.

## Covenant category

Use the lists in SEBI's "Guidance note on list of Covenants", Annex-VIA of the master circular for debenture trustees (see [the reference](#the-reference-for-covenant-categories) below for the exact file). Its six headings correspond to the categories as follows:

| Annex heading | Category |
|---|---|
| 1. Accounts/ funds/ reserves maintained | `accounts_funds_reserves` |
| 2. Financial | `financial` |
| 3. Affirmative | `affirmative` |
| 4. Affirmative or restrictive (credit rating, credit downgrade) | `credit_rating` |
| 5. Negative | `negative` |
| 6. Default | `default` |

Where the undertaking in a cell appears in one of the annex's lists of sub-types, use that heading's category, even where a gloss below would suggest another. Anything outside the lists is `other`.

Two glosses, where the annex's lists leave a choice:

- `financial`: a ratio or amount the issuer must keep within a limit, such as portfolio at risk, capital adequacy, debt to equity or return on assets.
- `other`: information and filing undertakings, such as non-submission of results or certificates; insolvency events; deliverables due after closing; and a clause cited only by its number, with no words of the undertaking.

Judge by what the undertaking requires, as the cell states it, not by the heading of the column or by how serious the failure seems. Read the annex itself before starting; this codebook does not reproduce it.

## Specificity

Judge the whole printed cell, not only the quoted part.

- `clause_text`: the undertaking in words, with any threshold, for example "(e) a Write-Off Ratio may not at any time increase above 6.5%".
- `requirement_and_actual`: both the required level and the level achieved.
- `clause_number_only`: a reference to a clause, with no words of the undertaking.
- `description_only`: names or paraphrases the failure without stating the term.

## Actions

Choose every kind the row's action columns report, and only those. Most rows have one or two. Write `none` if the action columns report no action at all. The action columns are those reporting what the trustee did or proposes to do: security enforcement, further action, and any extra column that reports action taken or a status of the matter.

- `cure_reported`: the cell says the breach was cured or the missing item supplied.
- `holders_meeting_held`: the cell reports a meeting of holders as held.
- `holders_meeting_scheduled`: the cell gives a meeting date that lies ahead of the report.
- `awaiting_instructions`: the trustee says it awaits holders' instructions.
- `follow_up_with_issuer`: the trustee says it is following up with the issuer.
- `waiver_reported`: holders or the trustee are reported to have waived the breach.
- `no_action_instructed`: holders are reported to have instructed no action.
- `reported_as_continuing`: the breach is reported as continuing.
- `nominee_director`: appointment of a nominee director is reported.
- `enforcement`: steps to enforce security or recover are reported.
- `other`: an action that fits none of the above.

Record the values as a list separated by `|`, in any order. Agreement is scored on the whole set.

## Row assignment

`true` only when which row, or which issuer, an ISIN belongs to depends on reading merged table cells. Otherwise `false`.

## Carried-over breaches

Give a quarter-end date (as YYYY-MM-DD) only when the row's own label assigns the breach to an earlier quarter, for example a heading or note saying that the row continues from it. Otherwise write `none`. Do not infer it from dates of breach or detection.

## Letters

- **Kind.** `meeting_continuation` when the letter continues or reconvenes a meeting of holders called earlier. Otherwise `breach`.
- **Quarter.** The quarter-end date the letter states for the breach or for the certificate it relies on, as YYYY-MM-DD. Write `none` when the letter states no quarter. Do not infer a quarter from the date of the letter.
- **Adjourned for lack of quorum.** `true` when the letter says a meeting of holders was adjourned, or could not proceed, for want of quorum. Otherwise `false`.

## Compliance statements

Each statement decision concerns the ISINs in the decision's `isins` column. Where one filing's statement treats some ISINs as exceptions and others not, the project records them as separate statements, so two decisions can point to the same page with different ISINs. Answer each for its own ISINs.

- **Made by.** Whoever signs the conclusion: `issuer` or `statutory_auditor`. The publisher may be someone else.
- **Scope.** As printed: `all_covenants` or `financial_covenants`.
- **Breach stated.** `true` when the statement lists any of these ISINs among its exceptions, or says that a covenant applying to them was not met.
- **ISINs printed.** `true` when the statement prints these ISINs. `false` when they are covered only by a general sentence, or only by not being listed among exceptions.

## Clause records

- **Category.** As for covenant category above.
- **Stage.** What the record is evidence of, judged from the document that quotes it:
  - `offered`: quoted from an offer document, that is a general or key information document or a placement memorandum;
  - `proposed`: a change put forward for approval, such as a proposed schedule of covenants;
  - `approved_in_principle`: a change approved, for example by an exchange under regulation 59, but not shown executed;
  - `executed_text`: quoted from an executed debenture trust deed or supplemental deed;
  - `described_in_force`: a party's quotation or description of a term it treats as in force, such as a trustee's letter quoting a clause, or an issuer's filing.

  These are different legal stages. An offer document does not show what was executed, an approval does not show that a change was made, and a description does not show what the contract says.

## Links between cells and clauses

Compare the trustee's cell with the clause record it is linked to.

- `consistent`: both state the same undertaking, with the same threshold where either gives one.
- `differs`: they state different terms, for example different thresholds or dates.
- `not_comparable`: one of them lacks what the comparison needs, for example the cell names the failure without the term.

## Handing in

Return the answers file with every decision you made, a reason for each hard case and for each decision you marked unsure, and the commit of this codebook given in the packet's instructions. Do not change the passage, locator or allowed values. A blank value means you could not decide, so give a reason; it is never a way of saying "none", which has its own value.

## The reference for covenant categories

The covenant categories come from one file. Use this file, not a later edition or a copy:

| | |
|---|---|
| Document | SEBI, Master Circular for Debenture Trustees, HO/17/11/12(2)2026-DDHS-POD1/I/22420/2026, 28 September 2026 |
| Official address | https://www.sebi.gov.in/sebi_data/attachdocs/sep-2026/1790593347737.pdf |
| SHA-256 of the file the project used | `4a8ce13addf1c5f9fb4dba3c7ab3e3a3e82660f2ae2906477b121b60b7e308f9` |
| Where | Annex-VIA, "Guidance note on list of Covenants", on page 71 of that file (the file's page, not the printed folio) |

Before any covenant-category decision, in either round (`breach_item.category` or `provision.category`), check that the file at the official address has that SHA-256 (for example with `sha256sum`). If the file cannot be downloaded, or its SHA-256 differs, make no category decision: tell the coordinator, and wait until they tell you how to go on. Do not use another edition, or a copy from anywhere else, unless the coordinator says so. You may carry on with other fields meanwhile. The coordinator records which file was eventually used, and its SHA-256, in the round's notes; nothing about it goes in `answers.csv`.
