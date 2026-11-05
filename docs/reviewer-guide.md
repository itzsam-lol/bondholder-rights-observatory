# Guide for the second annotator

Thank you for reviewing. This guide is all you need besides the packet's other files. Please read it, and the codebook, before you start.

## What you are asked to do

The Bondholder Rights & Disclosure Observatory records what public documents about Indian corporate bonds say: trustees' reports of covenant breaches, trustees' letters to bondholders, and issuers' statements of covenant compliance. Some of what it records is a judgement, such as which kind of covenant a report's cell describes, or whether a letter states a quarter. One person made all of those judgements. You are asked to make a set of them again, independently, from the documents themselves, so that the project can measure how often a second careful reader agrees.

You will not see the original answers, and you must not look for them. Until you have returned your answers, please do not open the project's repository, data, exports, reports or website, and do not discuss the decisions with anyone who made the original annotations. Do not use an AI tool or any automated aid to make or check a decision: the point of this review is your own reading of the source.

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
| `passage` | The text the project quoted from that spot, to help you find it. Read the source around it: rules often depend on words outside the quotation |
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
| `statement.breach_stated` | Whether the statement lists exceptions or says a covenant was not met | The statement and any annexure of exceptions |
| `statement.isins_printed` | Whether the statement prints the ISIN, rather than covering it only by a general sentence | The statement and its tables |
| `provision.category`, `provision.stage` | The clause's covenant category, and what kind of document quotes it | The clause and the document |
| `provision_link.agreement` | Whether the trustee's cell and the clause state the same term | Both passages |

Your packet's `README.txt` lists which of these fields it holds, with how many decisions of each.

## Working through the packet

1. **Get SEBI's annex.** The codebook names the file, its address, its SHA-256 and the page of the covenant categories. Download it and check its SHA-256, as below.
2. **Take one document at a time.** Sort `decisions.csv` by `document` and work through each document's decisions together.
3. **Download the document** from its `url` in an ordinary web browser, and save it. If a site refuses the download, try again later; do not use tools to get round a refusal.
4. **Check the file's SHA-256**, and compare it, ignoring case, with the `sha256` column:
   - macOS: `shasum -a 256 file.pdf`
   - Linux: `sha256sum file.pdf`
   - Windows PowerShell: `Get-FileHash file.pdf -Algorithm SHA256`

   If it differs, the publisher has changed the file. Do not answer that document's decisions; mark them `hash_mismatch` (below) and tell the coordinator.
5. **Go to the page and the locator.** Use the PDF viewer's page number, which can differ from the printed page number. Search for a few words of the passage if that helps.
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

A blank value means you could not decide at all. Leave a value blank only with a reason, and usually with a problem code. A blank is counted as unanswered, never as `none` and never as a disagreement.

### Reporting a source you cannot use

| `problem` | When |
|---|---|
| `source_unavailable` | The address does not serve the file, or the site refuses you |
| `hash_mismatch` | The file you downloaded has a different SHA-256 |
| `page_not_found` | The file has no such page, or you cannot find the locator or passage on it |
| `cannot_interpret` | The passage is there, but the document does not let you decide, for example because the text is illegible or contradicts itself |

Leave the value blank when you give `source_unavailable`, `hash_mismatch` or `page_not_found`. With `cannot_interpret` you may still give your best value, marked unsure.

## Returning your answers

Send only `answers.csv` to the coordinator, in the way you agreed. Keep the packet until the coordinator confirms that the answers arrived and could be read. Please do not send the downloaded documents, and do not publish the packet or your answers.

The coordinator will compare your answers with the original ones, field by field. Where they differ, a third person, or the coordinator, will decide, and record your value and reason beside the original and the decision. Your answers are never overwritten.

## About you

You are recorded only by the label the coordinator gives you, never by personal details. Please do not write personal information in `answers.csv`. Before you start, the coordinator will ask whether you agree that your answers may be released as part of the dataset under its licence, and how you would like to be credited, if at all.
