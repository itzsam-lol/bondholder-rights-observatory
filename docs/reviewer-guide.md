# Guide for the second annotator

Thank you for reviewing. This guide is all you need besides the packet's other files. Please read it, and the codebook, before you start.

## What you are asked to do

The Bondholder Rights & Disclosure Observatory records what public documents about Indian corporate bonds say: trustees' reports of covenant breaches, trustees' letters to bondholders, and issuers' statements of covenant compliance. Some of what it records is a judgement, such as which kind of covenant a report's cell describes, or whether a letter states a quarter. One person made all of those judgements. You are asked to make a set of them again, independently, from the documents themselves, so that the project can measure how often a second careful reader agrees.

This review is label-blind. The packet does not contain the original answers or the project's identifiers for its records. The original answers are, however, in the project's public repository, and could be found by searching for a bond's ISIN or a document's address. Keeping them out of your view depends on you, not on the packet: please do not look for them. Until you have returned your answers, please do not open the project's repository, data, exports, reports or website, and do not discuss the decisions with anyone who made the original annotations. Do not use an AI tool or any automated aid to make or check a decision: the point of this review is your own reading of the source.

There are no trick questions and no expected agreement rate. Where you disagree with what a rule seems to require, follow the rule and say so in your reason.

## What is in the packet

| File | What it is |
|---|---|
| `README.txt` | The round, the number of decisions, the commit of the codebook, and a table of the fields in this packet |
| `guide.md` | This guide |
| `codebook.md` | The rules for every field. Each decision names the rule that applies to it |
| `decisions.csv` | One line per decision: where to look and what to choose from. Do not edit it |
| `answers.csv` | One line per decision, for your answers. This is the only file you return |

The answer key is not in the packet and is not sent to you.

## The columns of `decisions.csv`

| Column | Meaning |
|---|---|
| `decision` | The decision's id for this round, such as `D0042`. Use it to find the matching line of `answers.csv` |
| `field` | What is being decided, such as `breach_item.category` (see below) |
| `kind` | `categorical` (one value), `binary` (`true` or `false`), `multi_label` (one or more values) or `date` |
| `allowed` | The values you may give, separated by `\|` |
| `multiple` | `true` if you may give several values |
| `document`, `url` | The document's id and the address to download it from |
| `sha256` | The SHA-256 of the exact file the project used. Check it before you start on a document |
| `page` | The page of the file, counted from 1 as a PDF viewer counts them, not the number printed on the page |
| `locator` | Where on the page: a row of a table, a covenant cell, the action columns, a letter's date, a statement's period, or a clause |
| `isins` | The bonds the decision concerns. Where one printed row is split into parts, they tell you which part |
| `passage` | For a report's covenant or action cell, or a clause, the project's transcription of the cell or clause being judged, to help you find it. Read the source around it: rules often depend on words outside the quotation. It is empty for every letter and every statement; for those, the page, the locator and the ISINs say where to look |
| `hard_case`, `hard_case_note` | Whether careful readers could reasonably differ here, and why. The note never says what to choose |
| `rule` | The section of `codebook.md` that applies |

## The fields

| Field | You decide | Look at |
|---|---|---|
| `breach_item.category` | Which kind of covenant the cell describes, using SEBI's annex | The covenant cell of the row |
| `breach_item.specificity` | How much of the term the cell prints | The whole covenant cell, not only the quoted part |
| `breach_item.assignment_uncertain` | Whether which row an ISIN belongs to depends on reading merged cells | The table's layout around the row |
| `breach_row.actions` | Every kind of action the row's action columns report | The action columns of the row |
| `breach_row.carried_over_from` | The earlier quarter, if the row's own label assigns the breach to one, or `none` | The row's label or note |
| `notice.kind` | Whether the letter is about a breach or continues an earlier meeting | The letter as a whole |
| `notice.period_end` | The quarter the letter states for the breach or the certificate, or `none` | The letter's text |
| `notice.adjourned_for_lack_of_quorum` | Whether the letter says a meeting was adjourned for want of quorum | The letter's text |
| `statement.made_by` | Who signs the statement's conclusion: the issuer or its statutory auditor | The signature and the conclusion |
| `statement.scope` | Whether the statement covers all covenants or financial covenants only | The statement's wording |
| `statement.breach_stated` | Whether the statement lists these ISINs among its exceptions, or says a covenant applying to them was not met | The statement and any annexure of exceptions |
| `statement.isins_printed` | Whether the statement prints these ISINs, rather than covering them only by a general sentence | The statement and its tables |
| `provision.category`, `provision.stage` | The clause's covenant category, and what kind of document quotes it | The clause and the document |
| `provision_link.agreement` | Whether the trustee's cell and the clause state the same term | Both passages |

Your packet's `README.txt` lists which of these fields it holds, with how many decisions of each.

## Working through the packet

1. **Get SEBI's annex.** The codebook names the file, its address, its SHA-256 and the page of the covenant categories. Download it and check its SHA-256, as below, before any covenant-category decision. If it cannot be had, or its SHA-256 differs, leave the category decisions for now, tell the coordinator, and do not use another edition or copy unless they say so. You may carry on with other fields meanwhile; nothing about the annex goes in `answers.csv`.
2. **Take one document at a time.** Sort `decisions.csv` by `document` and work through each document's decisions together.
3. **Download the document** from its `url` in an ordinary web browser, and save it. If a site refuses the download, try again later; do not use tools to get round a refusal, and do not use a copy from anywhere else. The coordinator will not send you copies of the documents. If the file still cannot be had, mark that document's decisions `source_unavailable`, as below: that is a result, not a failure.
4. **Check the file's SHA-256**, and compare it, ignoring case, with the `sha256` column:
   - macOS: `shasum -a 256 file.pdf`
   - Linux: `sha256sum file.pdf`
   - Windows PowerShell: `Get-FileHash file.pdf -Algorithm SHA256`

   If it differs, the publisher has changed the file. Do not answer that document's decisions; mark them `hash_mismatch` (below) and tell the coordinator.
5. **Go to the page and the locator.** Use the PDF viewer's page number, which can differ from the printed page number. For a letter, find the letter of that date that names the ISINs; for a statement, read the cited pages and any annexure. Where there is a passage, search for a few words of it if that helps.
6. **Decide by the rule.** Open the codebook section named in `rule`. Hard cases need extra care, and always a reason.
7. **Record your answer** on the matching line of `answers.csv`.

## Recording an answer

`answers.csv` has the columns `decision`, `field`, `value`, `unsure`, `reason` and `problem`. Fill in the last four. Do not change the first two, add or remove lines, or reorder columns. Keep the file as CSV in UTF-8; if you use a spreadsheet, save it back as CSV.

- **`value`**: exactly one of the allowed values, spelled as in `allowed`. Where `multiple` is `true`, give every value that applies, separated by `|`, in any order.
- **`unsure`**: `true` if a careful reader could reasonably choose differently from you, or you are not confident; otherwise `false`. Still give your best value when you are unsure.
- **`reason`**: required for every hard case, every answer marked unsure, every blank value and every problem. Elsewhere it is welcome but optional. A sentence is enough.
- **`problem`**: leave it empty unless something stops you, in which case use one of the codes below.

### `none` is a value; a blank is not

Some fields have `none` among their allowed values: a letter that states no quarter, a row with no carried-over label, a row whose action columns report no action. Writing `none` is a decision: you looked, and there is nothing to record.

A blank value means you could not decide at all. Leave a value blank only with a reason, and usually with a problem code. A blank with no problem code is counted as unanswered; a blank with a problem code is recorded as excluded for that reason. Neither is ever counted as `none` or as a disagreement.

### Reporting a source you cannot use

| `problem` | When |
|---|---|
| `source_unavailable` | The address does not serve the file, or the site refuses you |
| `hash_mismatch` | The file you downloaded has a different SHA-256 |
| `page_not_found` | The file has no such page, or you cannot find the locator or passage on it |
| `cannot_interpret` | The passage is there, but the document does not let you decide, for example because the text is illegible or contradicts itself |

Give at most one code, written exactly as above. Do not combine codes or use any other word: a line with an unrecognised or combined code is not scored.

Leave the value blank when you give `source_unavailable`, `hash_mismatch` or `page_not_found`; a value given with one of them is not scored. With `cannot_interpret` you may give your best value, and must then write `true` in `unsure`; with no value, the decision is recorded as excluded, not as unanswered.

`source_unavailable` means you could not get the file; `cannot_interpret` means you have the right file and page, but the document does not let you decide. Do not use one for the other.

## Returning your answers

Send only `answers.csv` to the coordinator, in the way you agreed. Keep the packet until the coordinator confirms that the answers arrived and could be read. Please do not send the downloaded documents, and do not publish the packet or your answers.

The coordinator will keep your answers private, and use them only to compare with the original annotations, field by field, and to decide, with a reason, where the two differ. Your answers are never overwritten. Your answers, your reasons and your identity will not be put in the project's public data or published in any form unless terms for that have been agreed with you and the project has taken legal advice. Neither has happened yet.

## About you

Your answers are kept under a label the coordinator gives you, never with personal details. Please do not write personal information in `answers.csv`. Whether your answers could ever be published, under what licence, how you would be credited, if at all, and how long they are kept are not yet settled; the coordinator will not ask you to agree to any of them until legal advice has been taken.
