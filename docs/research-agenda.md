# Research agenda

This document sets out what the evidence collected so far implies, and where the project should go next. It builds on the first release's [research design](research-design.md) and on two later passes made on 4 November 2026. Statements about Indian sources are backed by records in `data/` or by passages checked against the source, named here by their identifiers. Statements about other work rest on the publications cited.

## In brief

- **The public record of a bond's protections is a chain of statements.** An issuer measures its covenants, its auditor gives limited assurance, the issuer sends the result to its trustee, and the trustee reports breaches and writes to holders. Holders then meet, waive, or do nothing. An exchange approves any change to the terms, and the trust deed sits behind all of it.
- **Different publishers are not different evidence.** By the trustees' own printed definitions, the dates in their breach reports are the dates of the issuer's certificate. In every case examined where the issuer's statement and the trustee's report agree, the trustee's detection is dated on or after the issuer's material reached it. Agreement there shows that a statement was passed on faithfully. It does not confirm it.
- **Independent information is visible where the chain diverges.** A trustee reports a governance breach that the auditor's conclusion does not reflect. A trustee reports a clause the auditor's annexure does not name. An issuer reports a breach that the trustee's report omits.
- **The executed contract is not the only ground truth, but it is still the only operative one.** Amendment approvals and descriptions can reconstruct much of a covenant's history. For one instrument they cannot settle which limit applied on the test date that mattered.
- **A denominator now exists for one trustee and quarter.** Catalyst's own census of the issues it monitors prints 1,832 ISINs; its breach report lists 44 of them.
- **For most breaches, the published record stops before any outcome.** No trustee publishes a cure of a financial covenant; the cures published are late filings made good. For every ISIN Catalyst listed, no outcome is published at all.
- **Each party adds what it alone holds.** Where issuer and trustee agree that a breach occurred, the trustee adds the deed's wording, references and dates, and the issuer the measured level.
- **What was public when can now be reconstructed.** Every document carries an availability date, and the record can be viewed as it stood on any date.

## The disclosure chain, and why it is the right object of study

The first release asked how far a reported breach could be traced back towards the contract. The second found a second publisher, the issuer. The third shows that the two publishers are links in one designed chain:

| Link | What is published | Who makes it | Rule checked in this release |
|---|---|---|---|
| Covenant measured | The issuer's statement of compliance, often with required and actual levels | Issuer's management | `issuer-covenant-compliance-status` |
| Measurement reviewed | The statutory auditor's certificate, in negative form | Auditor, limited assurance | `lodr-auditor-certificate-covenants` |
| Statement transmitted | The trustee's record of when each issuer's compliance report arrived (Table 3) | Trustee | `trustee-table-3` |
| Breach reported | The trustee's breach report (Table 5) and letters to holders | Trustee | `table-5-format` |
| Holders consulted | Notices of meetings, adjournments, instructions, waivers | Trustee, holders | `default-at-isin-level` |
| Terms changed | Application, exchange approval in principle, amendment deed | Issuer, exchange, trustee, holders | `lodr-material-modification`, `lodr-modification-consent` |
| Published on the issuer's site | All compliance reports filed | Issuer | `lodr-website-compliance-reports` |

Studying the chain rather than the bond changes what can be measured. Each link can be examined on four separate questions:

1. **Visibility:** can an outsider see the link at all?
2. **Dependence:** does it repeat an earlier link or add to it?
3. **Fidelity:** does the contractual meaning survive the passage?
4. **Closure:** does the chain reach an outcome?

These questions also make the project's identity coherent. It is an audit of a mandated disclosure chain, made with an evidence graph that keeps attribution, lineage and legal stage explicit. The dataset is the instrument of that audit, not a bond database.

## Corroboration or repetition

### The evidence of dependence

- **Rules.** The master circular routes the issuer's auditor-certified compliance status to the trustee each quarter, and the trustee's monitoring of breaches follows (`issuer-covenant-compliance-status`).
- **Definitions printed by trustees.** Catalyst's breach report says "Date of Actual Breach is considered as Quarter for which covenant certiticate [sic] has been submitted". IDBI's says the date of actual breach is "the date of the certificate of Statutory Auditor or the due date for submission", and the date of detection is "the date of the receipt of the certificate from the issuer company". Both are printed notes in the transcribed reports.
- **Dates.** For the 22 comparisons between an issuer's statement and the trustee's report for the quarter ended 30 June 2026, the dataset records:
  - the statement's own date;
  - where Catalyst's census has been measured, the date Catalyst records receiving the issuer's quarterly compliance report;
  - the trustee's date of detection.

  In all 17 agreements, detection is on or after one of the earlier two.
- **Citations.** In 6 of the 17, the trustee's row names "the security cover certificate by the statutory auditor" as its basis.

| Issuer | Statement dated | Report received by trustee | Trustee's detection | Outcome |
|---|---|---|---|---|
| Dvara KGFS (10 ISINs, Catalyst) | 12 Aug 2026 | 31 Jul 2026 | 24 Aug 2026 | Agree |
| Dvara KGFS (1 ISIN, IDBI) | 12 Aug 2026 | not measured | 13 Aug 2026 | Agree |
| SATYA MicroCapital (6 ISINs) | 14 Aug 2026 | 14 Aug 2026 | 14 Aug 2026 | Agree; the trustee cites the certificate |
| SATYA MicroCapital (INE982X08042) | 14 Aug 2026 | not in the census | none | Only the issuer reports a breach |
| Infinity Fincorp (2 ISINs) | 7 Aug 2026 | 12 Aug 2026 | 13 Aug 2026 | Disagree |

So the 17 agreements are best read as **transmission**: the issuer's exception reached the trustee's report. That is worth measuring. It shows the chain working, and differences of level within an agreement (two Dvara ISINs) show where meaning shifts in transit. It is not independent confirmation of the issuer's statement.

### Where independent information appears

- **Infinity.** Catalyst received the issuer's quarterly compliance report on 12 August and dated its detection of a governance breach 13 August. The auditor's report of 7 August had concluded that nothing suggested non-compliance with all covenants. The trustee's information evidently came from something other than the auditor's conclusion, perhaps the compliance report itself. The record does not say.
- **Satya, row 11.** The trustee reports breaches of clause 9.8 (ii) and (iii) for two ISINs, detected a week after the certificate, which names only clause 9.3 for them. The ISIN-level comparison counts these ISINs as agreeing. At clause level, the trustee adds a breach the certificate does not show.
- **INE982X08042.** The issuer's auditor reports a breach; the trustee's report and its census omit the ISIN, which the issuer says was redeemed on 8 July.

### What this changes

- Comparisons must record lineage, not just agreement. The dataset now does, per comparison: statement date, receipt date, detection date, and whether the trustee cites the certificate.
- Corroboration needs sources whose information does not run through the certificate. Candidates are:
  - rating agency findings, which rest on their own surveillance;
  - financial results, from which some ratios can be recomputed;
  - holders' meeting outcomes;
  - other lenders' notices, where disclosed.

  None is yet collected systematically.
- An issuer's assertion, an auditor's limited-assurance conclusion and a trustee's report are different kinds of evidence even about the same ISIN and quarter. They should never be counted as three confirmations.

## What counts as independent here

Independence has to be judged fact by fact, by where each fact originates, not by who publishes it.

| Fact | Where it originates | Who republishes it | What could corroborate it without passing through the same origin |
|---|---|---|---|
| A covenant was not met | The issuer's measurement from its books | Auditor (limited assurance), trustee | Recomputation from financial results prepared for another purpose, which still needs the deed's definition of the ratio |
| The required level and wording | The executed deed | Trustee, issuer, exchange letter | The deed itself, or two parties that each hold it |
| The measured level | The issuer's books | Rarely the trustee | Financial results, where the ratio is defined the same way |
| The deed and its amendments | The executed instruments | Trustee's letters, issuer's annexures | The instruments, an exchange approval, holders' resolutions |
| Holders' decisions | Holders' votes | Trustee's letters, later reports | Meeting outcomes published by the trustee, or exchange filings |
| A change was approved | The exchange's decision | Issuer's intimation | The exchange's own notice |

For the fact the dataset compares most often, that a covenant was not met, no fully independent public source exists. Every published statement descends from the issuer's own measurement. The nearest thing to an independent check is consistency between documents the issuer prepared for different purposes, and that check needs the ratio's contractual definition, which sits in the unretrieved deed.

Facts that originate elsewhere can be corroborated. That includes holders' votes, exchange approvals, and the deed's wording where two parties each hold the deed.

## Transmission and addition, field by field

For the 17 agreements, `brdo report` records which party prints each kind of information:

| Information | Trustee only | Issuer only | Both | Neither |
|---|---|---|---|---|
| Obligation wording | 12 | 0 | 1 | 4 |
| Clause reference | 10 | 1 | 5 | 1 |
| Deed dates (trustee's letters) | 9 | 0 | 6 | 2 |
| Required level | 4 | 0 | 9 | 4 |
| The issuer's measured level | 0 | 8 | 1 | 8 |

The fact of the breach passes through the chain. What each party adds is what it alone holds: the trustee holds the deed and prints its wording, references and dates; the issuer holds its books and prints the measured level. The trustee repeats that level in one of the nine cases where the issuer prints one.

Two parties can therefore be dependent on one fact and complementary on others, and a reader who wants both the obligation and the measurement needs both publications. The rules behind the table are mechanical and stated in `consistency.field_flows`.

## Closure, typed by what was resolved

The published follow-up is counted state by state, never merged. For the quarter ended 30 June 2026:

- **No trustee publishes a cure of a financial covenant.** All 24 published cures concern other obligations, mostly late filings later made (IDBI).
- **The outcomes published are few.** Holders instructed no action for 6 ISINs (Vistra). A waiver is reported for 2 (Axis, Vistra) and a nominee director for 1 (MITCON).
- **For all 44 of Catalyst's ISINs, no outcome is published.** Meetings were scheduled for 39, adjourned for lack of quorum for 15, and instructions are awaited for all 44.

A failed meeting, a late filing made good, a waiver and a restored ratio are different kinds of closure. The record mostly shows the first two.

## What a trustee treats as a breach

Catalyst's census marks the issuer's quarterly compliance report as not received for 59 ISINs. Its breach report for the same quarter lists 2 of them. IDBI's breach report, by contrast, lists non-submission of financial results as breaches.

Whether a missing compliance report breaches a particular instrument's terms depends on its deed, so this is not a finding that anything went unreported. It is a measured difference in what two trustees publish as breaches, and it bears on any comparison across trustees.

## What was public when

Each document now carries an availability date, estimated from a listing page or the server's Last-Modified header, or failing those from its own date as a lower bound. `brdo status --as-of` and `brdo show --as-of` use only what was public by a date, so a later version cannot leak into an earlier account. This is the hindsight problem that real-time datasets in macroeconomics address, for example Croushore and Stark (2001, *Journal of Econometrics*).

- **Breach reports are late in the files held.** The trustees' report files for the quarter ended 30 June 2026 date from 72 to 111 days after the quarter end. Most detections in them fall between June and September 2026, and some rows carry detections from 2023 and 2024.
- **The issuer's account comes first.** In all 21 comparisons with a listing, the issuer's statement was public before the trustee's report, so for a time the public record held the issuer's account alone.
- **A document's own date is not its publication date.** Dvara's regulation 59 intimation is dated 2 July 2026, but the copy on the issuer's site was last modified on 3 August. Its date of publication depends on the channel, and an exchange may have disseminated it earlier.
- **Last-Modified dates the version held.** An earlier version may have been published sooner, so these are measurements of the files held, not findings about anyone's timeliness.

## The comparison sample: a first pilot

Logged searches covered four of the twenty sampled ISINs, issued by Power Finance Corporation, LIC Housing Finance, Shriram Finance and Godrej Finance. For the first three, filings for the quarter surfaced only on NSE, which the project excludes, and trustees' certificates for some of them surfaced there too. For Godrej Finance only other group companies' filings surfaced. LIC Housing Finance's own debenture pages, as served to the project's client, linked no such filing.

The breach-listed sample's statements, by contrast, came from smaller issuers' own sites. Four issuers cannot support a conclusion. The pilot does suggest that the channel through which an outsider can see a statement differs with the issuer, and that for large issuers it may run through the exchange.

## What each kind of statement can establish

| Statement | What it is | What it can establish | What it cannot |
|---|---|---|---|
| Issuer's statement of covenant compliance | Management's assertion | What the issuer says it measured, and the exceptions it admits | That the measurement is right |
| Auditor's certificate | Limited assurance in negative form ("nothing has come to our attention…") | That the auditor found nothing contrary within its procedures, which rely on management representations | Compliance; covenants outside its stated scope |
| Trustee's breach report | The trustee's record of breaches it detected, largely from issuer certificates | That the trustee recorded a breach, and when | That no other breach occurred; independent confirmation of the certificate |
| Trustee's letter citing an amendment deed | The trustee's description of the deed | That the trustee treats a deed of that date as amending the terms | The deed's text |
| Exchange's approval in principle | Approval of a proposed modification, subject to conditions | What was proposed and approved in principle, and the existing term as the application described it | That the modification was executed, or from when it applies |
| Rating rationale | The agency's own analysis | What the agency took note of | Per-ISIN covenant status, unless it says so |

Satya's certificate states the standard it follows: the Institute of Chartered Accountants of India's *Guidance Note on Reports or Certificates for Special Purposes (Revised 2016)*. It also says that the assurance obtained "is substantially lower than" a reasonable assurance engagement would give (`satya-qcr-2026-06`, page 18, read from the rendered page).

## Contract versions: what public traces can and cannot settle

Every clause record now states what it is evidence of (`Provision.stage`):

- `executed_text` from the contract itself;
- `described_in_force` by a party;
- `proposed`;
- `approved_in_principle`.

Of 25 clause records, 24 are descriptions and 1 is an approval in principle. None is executed text.

For INE179P08082 the public trail settles a great deal. BSE's letter describes the existing limit as "less than 70% … until the Final Settlement Date". It records a proposed waiver of the breach "until the date of execution of the Amendment Deed", and a schedule that applies "commencing from the date of execution of the Amendment Deed". The trustee dates that deed 29 July 2026.

On the project's reading, which is an annotation and not a finding, the test at 30 June 2026 preceded the deed. The existing limit would then have applied on that date, with its breach waived. The issuer's statement for that date prints ≤85%, which is the proposed step for the period to 31 March. The trustee's report prints "less than 80%" until the Final Settlement Date. Which limit operated on 30 June depends on whether the executed deed treats the period before its execution differently. No public document found settles that.

This is the general lesson. Approval trails reconstruct what was proposed and approved, and often what was in force before. Without the executed deed, they rarely establish the operative term on a particular test date.

## Denominators, kept apart

| Population | What it is | Size in this release | Use |
|---|---|---|---|
| Breach-selected sample | ISINs listed in reviewed trustees' breach reports for the quarter, plus a few related ISINs | 96 ISINs, 93 of them listed | Tracing reported breaches |
| A trustee's monitored population | ISINs printed in the trustee's own table of compliance reports received | 1,832 ISINs for Catalyst, quarter ended 30 June 2026 | Denominator for that trustee's reports; sampling frame |
| Comparison sample | 20 ISINs from Catalyst's census that its breach report does not list, drawn by a fixed, reproducible rule | 20 ISINs, listed in `monitoring-censuses.yaml` | The next study: are unreported instruments as observable? |
| Listed debt market | All listed debt ISINs | Not measured | Not available from a source the pipeline may use |

Catalyst's breach report lists 44 ISINs, 2.4% of the ISINs printed in its census, and its census prints 43 of those 44. A listing is a trustee's report of a breach. It is not a breach rate, and it says nothing about other trustees.

## Observability, dimension by dimension

The project does not combine these dimensions into a score. They fail for different reasons and call for different remedies, and a weighting would need a justification that nothing here supplies. The FAIR principles for research data keep findability, accessibility, interoperability and reusability apart for the same reason.

| Dimension | What the project records | Where |
|---|---|---|
| Discoverability | Every search, its query or listing page, and its outcome | `searches.yaml` |
| Browser accessibility | Whether a source serves people; manual-only sources | `sources.yaml` |
| Automated retrievability | The policy per source, and refusals observed (BSE, one issuer) | `sources.yaml`, `searches.yaml` |
| Readability | Text layer audit: outlined text, scans, OCR | `brdo verify` |
| Matchability to an ISIN | Whether a statement prints the ISIN or covers it only by a general sentence | `isins_printed` fields |
| Traceability | Every claim anchored to a page; machine-verified or read from a rendering | `evidence.csv` |
| Reusability | Redistribution, quotation limits, AI-training reservations | `sources.yaml` |
| Persistence | File hashes re-checked at source; listing pages that keep old quarters | `brdo fetch`, search notes |

On persistence, Catalyst's page of compliance-report tables lists a file for every quarter back to the quarter ended 30 June 2024. The page holds the past as well as the present, which makes a lawful look backwards possible.

## Directions, in order of value

### 1. A lineage-aware corroboration study

For the sample's issuers, over several quarters, collect three things: the issuer's statement from its regulation 62 page, the trustee's receipt date from its census, and the trustee's breach report. Classify each pair as transmission, divergence or addition.

Add at least one source whose information does not run through the certificate. Rating rationales, financial results and holders' meeting outcomes are the candidates.

- **What it would show:** how faithfully the chain carries exceptions, and how often the trustee adds information of its own.
- **Risk:** the scope of each statement must keep deciding what is comparable.

### 2. Covenant versions with legal stages

For each ISIN with a sign of change, collect regulation 59 intimations, exchange approvals, holders' resolutions and trustees' letters. Record each as a clause at its stage. For each test date, report whether the operative term is established by executed text, consistently described, or undetermined.

### 3. The comparison sample

Apply the observability protocol to the 20 sampled ISINs, then to samples from other trustees' censuses.

- **What it would show:** whether covenants of unreported instruments are as visible as those of reported ones.
- **What it would not show:** how common breaches are.

### 4. Longitudinal capture

Catalyst's archive of eight earlier quarters makes a backward look possible now. Capture every disclosure page each quarter after that, hash every file, and record removals. The eight-quarter archive may also show whether past listings persist or are revised.

### 5. The semantics of trustee reports

Document how every trustee with a public report defines its date columns, carried-over rows, "no information" and further action. Two trustees' definitions already show the dates are certificate dates. SEBI's expert working group invited suggestions until 15 July 2026 (`expert-working-group-suggestions`), so this would be a public research note.

### 6. Later: an evaluation set

Only after independent double annotation with measured agreement, excluding sources that reserve AI-training rights. Real tasks from this corpus include:

- recovering tables from outlined or scanned files;
- extracting exception lines;
- telling transmission from divergence;
- separating a clause's stage from its wording.

## What not to do

- Do not count publications by different parties as independent confirmations.
- Do not treat an approval, a proposal or a description as the operative contract.
- Do not get around access controls to build a contract corpus; the closure is itself a finding.
- Do not estimate breach prevalence, or rank issuers or trustees.
- Do not republish whole tables or documents because their content is factual. The census is measured and sampled, not reproduced.
- Do not collect personal data that documents happen to contain. A test now fails if the published records contain e-mail addresses, depository participant IDs, PANs or phone numbers in common written forms.

## What a recognisable contribution would look like

- **A data descriptor** for the evidence graph, with a datasheet, hashes and the access log.
- **A methods paper on auditing mandated disclosure chains,** treating visibility, dependence, fidelity and closure as separate measurements. India's corporate bond market is the case.
- **A research note on what trustee report fields mean,** for regulators and trustees.
- **Later, an evaluation set.**

Novelty has been assessed only against logged searches. The project should keep claiming no firsts.

## Connections to existing work

- **Covenants and their measurement.** Smith and Warner (1979, *Journal of Financial Economics*) set out the theory of bond covenants. Later work relied on purpose-built data:
  - Dichev and Skinner (2002, *Journal of Accounting Research*) used a loan database;
  - Billett, King and Mauer (2007, *Journal of Finance*) and Reisel (2014, *Journal of Corporate Finance*) used a bond-issue database with covenant fields;
  - Chava and Roberts (2008, *Journal of Finance*), Roberts and Sufi (2009, *Journal of Finance*) and Nini, Smith and Sufi (2012, *Review of Financial Studies*) found violations by searching regulatory filings;
  - Bradley and Roberts (2015, *Quarterly Journal of Finance*) studied how covenants are priced.

  The Indian chain described here is the nearest public analogue of that infrastructure, and the project measures how much of it an outsider can use.
- **What summaries lose.** Ivashina and Vallée (2020, NBER Working Paper 27316) show that carve-outs in loan contracts matter as much as headline covenants. A trustee's one-line description of a breach is exactly such a summary.
- **Public is not the same as usable.** Blankespoor, deHaan and Marinovic (2020, *Journal of Accounting and Economics*) review evidence that the cost of processing disclosures shapes who uses them.
- **Dependence and provenance.** Bovens and Hartmann (2003, *Bayesian Epistemology*, Oxford University Press) show how far agreement between reports supports a conclusion depends on whether the reports are independent. The W3C PROV data model (2013) gives a standard vocabulary for recording which statement was derived from which. The lineage fields here are a small, domain-specific version of that idea.
- **Assurance.** The international standard for assurance engagements other than audits, ISAE 3000 (Revised), separates reasonable from limited assurance. Satya's certificate follows an ICAI guidance note and draws the same distinction.
- **Data stewardship.** The FAIR principles (Wilkinson et al., 2016, *Scientific Data*) and datasheets for datasets (Gebru et al., 2021, *Communications of the ACM*).
- **Contract datasets in machine learning.** CUAD (Hendrycks et al., 2021), LEDGAR (Tuggener et al., 2020) and ContractNLI (Koreeda and Manning, 2021) are built from contracts filed with the US SEC. EDGAR publishes a policy for declared programmatic access, so the absence of comparable Indian resources may owe as much to access regimes as to the documents.
- **Disclosure infrastructure elsewhere.** The EU's European single access point (Regulation (EU) 2023/2859) is designed to give centralised, machine-readable access to public disclosures. It is a policy contrast, not a model this project can adopt.
