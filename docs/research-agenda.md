# Research agenda

This document sets out where the project should go next, and why. It builds on the first release's [research design](research-design.md) and on a second pass, made on 4 November 2026, that looked beyond the trustees' reports. Statements about Indian sources are backed by records in `data/` or by passages checked against the source, named here by their identifiers. Statements about other work rest on the publications cited.

## What the first release measured, and what it could not

The first release measured backward traceability. Starting from breaches that trustees reported for the quarter ended 30 June 2026, it asked how far each could be followed towards the contract. The answer was a long way, and then a hard stop. Trustees' letters gave a deed date for 52 of 93 ISINs, but no contract could be retrieved through the pipeline.

That design has three blind spots.

- **It can only see what one party says.** Most of its comparisons set a trustee's report against the same trustee's letters. Agreement there (24 of 24 levels) is close to guaranteed and corroborates little.
- **It treats the contract as the only ground truth.** The trace either reaches the deed or fails. Yet amendment approvals, issuers' own statements and auditors' certificates are also public evidence of what the contract says and when it changed.
- **It cannot say anything about instruments without a reported breach.** The sample is chosen on the outcome.

## What the second pass found

### An independent channel exists: the issuer's own statement

The master circular requires issuers to give their trustee, every quarter, "the compliance status with respect to financial covenants … certified by the statutory auditor". The LODR Regulations require a statutory auditor's certificate that covers "compliance with all the covenants" (regulation 56(1)(d)). They also require the compliance reports an issuer files to be on its website (regulation 62(1)(g)). These are references `issuer-covenant-compliance-status`, `lodr-auditor-certificate-covenants` and `lodr-website-compliance-reports`.

So for every quarter there should be a second, independent public statement of whether each listed ISIN's covenants were met. For the quarter ended 30 June 2026, logged searches covered 11 issuers in the sample:

- **Retrieved for 3:** Dvara KGFS, Infinity Fincorp and SATYA MicroCapital.
- **Located but blocked for 1:** Pahal's server answered HTTP 403 to the project's identified client.
- **Not found for 7:** Aye, Akara, Light, NeoGrowth, Samunnati, Konkan Railway and Meghalaya Energy.

Most of the searches used a general search engine. That is a weak protocol, and a check of each issuer's regulation 62 page would be better. Two issuer pages were checked directly: Satya's held the statement, and Aye's listed none in the page served.

Setting the three retrieved statements beside the trustees' reports gave 22 ISIN-level comparisons:

| Outcome | Comparisons | Cases |
|---|---|---|
| Both report a breach | 17 | All 11 Dvara ISINs the trustees list appear among the issuer's own exceptions; 6 Satya ISINs |
| Disagree | 3 | Infinity's auditor reports compliance with all covenants for two ISINs the trustee lists. Satya's auditor reports a breach for INE982X08042, which the trustee's report does not list |
| Cannot be compared | 2 | Infinity's management statement covers financial covenants only, and the trustee lists a governance undertaking |

The agreements are detailed. For INE982X07432 the issuer's auditor names "Clause 17.4 (a)(i), (v), (ix), (x) & (xiii)", the same sub-clauses as the trustee. For INE179P07589 IDBI prints a return on assets of −1.02% against 1%, and so does the issuer. IDBI's "date of actual breach", 12 August 2026, is the date of the issuer's statement. That matches IDBI's own printed definition of the column and is independent evidence of what the column means.

The disagreements are the kind a single-source design cannot see:

- **Infinity (`infinity-governance-covenant`).** The trustee lists both ISINs for breach of an undertaking to follow corporate governance requirements and the RBI's fair practices code. It gives 30 June 2026 as the date of breach and 13 August as the date of detection. Six days before detection, the issuer's auditor gave limited assurance that nothing suggested non-compliance with all covenants at that date.
- **INE982X08042 (`satya-ine982x08042-not-in-trustee-report`).** The issuer's auditor reports it as non-compliant at 30 June 2026. The issuer's report to the trustee lists it under that trustee's deeds, and says it was fully redeemed on 8 July. The trustee lists a sister ISIN with the same clause and the same redemption date, but not this one.
- **Deed histories (`satya-deed-history`).** For two of six Satya ISINs, the trustee's letters and the issuer's certificate disagree about which deeds and amendments govern. For INE982X07457, the date the trustee cites as the deed is, according to the issuer, an amendment.

None of these is evidence that anyone erred. Each has ordinary possible explanations: scope, timing, redemption, or how a document was drafted. Each also changes what an outsider can conclude from either source alone.

### Contract versions leave public traces even when contracts do not

Regulation 59 of the LODR Regulations bars material modification of listed debentures without the exchange's prior approval. That approval comes only after the board, the trustee and holders of three-fourths by value have agreed (`lodr-material-modification`, `lodr-modification-consent`). An amendment therefore leaves a trail: an application, an in-principle approval, the issuer's intimation, a holders' resolution and a trustee's letter.

For INE179P08082 that trail resolves most of what the first release recorded as unexplained. The issuer's intimation of 2 July 2026 annexes BSE's letter of 1 July. The letter describes the existing provision as a cost-to-income ratio of "less than 70% … until the Final Settlement Date". It describes the proposed change as a waiver of the breach followed by ≤85% until 31 March 2026, ≤80% until 30 September 2026 and ≤70% thereafter. The trustee's later letter matches that schedule and dates the amendment deed 29 July 2026.

Two statements still do not fit. The trustee's quarterly report quotes "less than 80%" until the Final Settlement Date, which matches neither version. The issuer's own statement for 30 June prints ≤85%, the proposed level for the period to 31 March. Both stay open in `dvara-cost-to-income-limit`. The deed itself has not been retrieved, so the reconstruction rests on BSE's description of it. The provisions file records it that way, as a description in a letter rather than the text of the deed.

This suggests the most promising route to the contract dimension is not the contract. It is the amendment channel, which is designed to be public.

### Trustees publish more per-ISIN structure than the first release used

The master circular prescribes eight website tables (`trustee-table-3`, `trustee-table-1-rating-links`). Table 1 links each rating revision to the agency's press release. Table 2 records payment status. Table 3 lists, by entity and ISIN, whether each quarterly compliance report and security cover certificate was received. Table 8 records defaults and the trustee's action.

Table 3 matters most. It is a per-trustee census of monitored issues, which makes possible a comparison sample of instruments without a reported breach, drawn lawfully from trustees' own sites. Table 4, by contrast, gives only counts.

The prescribed Table 5 heading says "breached during the quarter" (`table-5-during-the-quarter`). That is a further reason to treat rows carried over from earlier quarters, which some trustees print, as a distinct case.

### The rating-agency channel is narrower than secondary sources suggest

A search summary stated that SEBI requires every rating press release to explain the instrument's covenants. The master circular for rating agencies says otherwise. A detailed explanation of all covenants is required for credit-enhanced ratings (paragraph 14.3), and covenants assumed must be disclosed for structured finance products (paragraph 10.1.10). Some agencies include covenant annexures more widely, but that is practice, not a uniform rule, and it has not been assessed here. A rationale can still state a covenant and note its breach, as ICRA's rationale for Konkan Railway does for a debt service coverage covenant (`icra-krcl-139196`).

### Access is a property of each publisher, not of a type of source

Issuer websites are not uniformly open. Pahal served its home page but refused its filings to an identified client, and Aye's disclosure list did not appear in the page served. Openness can also cut the other way. Satya's quarterly report to its trustee, published on its own site, prints hundreds of individual debenture holders' names and addresses next to the covenant certificate. Easy access is not a licence to collect everything a file contains.

## A sharper formulation

The first release's question still stands:

> For listed Indian non-convertible debentures, how much of the path from a contractual protection to a reported breach of it can an independent researcher reconstruct from public sources, and exactly where does that path break?

The second pass suggests three questions beneath it, each answerable with this design:

1. **Corroboration.** When two independent channels that are each mandated to report on the same covenant and quarter can both be read, do they agree? On which of: whether a breach occurred, which undertaking, the required level, and which version of the deed?
2. **Versioning.** Can the operative version of a covenant at a given test date be reconstructed from public amendment traces, without the executed deed?
3. **Comparability.** Are the same measures as observable for instruments that no trustee has reported, drawn from trustees' own census tables?

### Why the dimensions are not combined into one score

A document can exist, be discoverable, be readable in a browser, be retrievable by a declared program, be reusable under its terms, and stay unchanged over time. These are different properties, and they fail for different reasons and call for different remedies. A single index would hide which barrier binds. The FAIR principles for research data, which separate Findable, Accessible, Interoperable and Reusable, are a useful precedent for keeping them apart. They are also a reminder that a regulatory disclosure can be fully public and still not machine-actionable.

The project therefore reports each dimension separately, per channel and per instrument. A composite would need a defensible weighting, which nothing here supplies.

## Evidence channels

| Channel | What it says about a covenant | Basis checked in this release | Access observed |
|---|---|---|---|
| Trust deed, key information or offer document | The terms | Not assessed for issuers' websites | BSE browser only; NSE forbidden; SCMS credentialed |
| Amendment approval and intimation (LODR 59) | A change to the terms, with old and new wording | `lodr-material-modification` | Issuer website (one case retrieved); exchange browser only |
| Trustee breach report (Table 5) and letters | That a breach was found, with clause text or a description | `table-5-format`, `trustee-status-report` | Trustee websites, open |
| Trustee monitoring tables (Tables 1, 2, 3, 8) | Per-ISIN census, rating links, payments, defaults | `trustee-table-3`, `trustee-table-1-rating-links` | Trustee websites; not yet transcribed |
| Issuer's covenant compliance statement and auditor's certificate | Whether each covenant was met, sometimes with levels | `issuer-covenant-compliance-status`, `lodr-auditor-certificate-covenants`, `lodr-website-compliance-reports` | Issuer websites; open for 3 of 11 issuers searched |
| Rating press release | Covenants for credit-enhanced and structured ratings; sometimes breaches | `cra-covenants-credit-enhanced`, `cra-covenants-structured-finance` | Agency websites; terms vary |
| Depository ISIN pages | Identity, terms, trustee as recorded | Not a regulatory reference | Manual only |
| Bond Central | Described as a public repository of documents and disclosures | `bond-central-scope` | Unreachable on 3 and 4 November 2026 |
| Company registry charge filings | May attach the instrument creating a charge | Not assessed | Not assessed |

## Directions, in order of value

### 1. A two-channel corroboration study

Check the issuer's regulation 62 page directly, not through a search engine, for every issuer in the sample, for two to four quarters. Record each covenant statement beside the trustee's report for the same quarter, using the comparison that `brdo report` now computes.

- **What it would show:** how often two mandated, independent public statements agree, and on what. This is the clearest measure of whether the public record can be relied on without the contract.
- **What it needs:** the regulation 62 page protocol; transcription of scanned annexures from rendered pages; a manual queue for blocked sites.
- **Risks:** issuer statements are self-reports given limited assurance, not audits. Statements limited to financial covenants cannot answer other kinds of breach, and the comparison must keep reporting those as not comparable rather than as agreement.

### 2. Reconstructing covenant versions from amendment traces

For each ISIN with any sign of a change (a waiver, a revised level, a cited amendment deed), collect the issuer's regulation 59 intimations, trustee letters and holders' meeting outcomes. Record each version as a provision that amends the last, with dates only where the source states them.

- **What it would show:** whether an outsider can tell which version applied at each test date, which matters more to a holder than the original deed.
- **Risks:** approvals in principle are not executed amendments. Exchange letters annexed to issuer filings carry the exchange's own terms of reuse.

### 3. A comparison sample from trustees' census tables

Draw a random sample of ISINs from the same trustees' Table 3 for the same quarter, excluding those in Table 5, and apply the same protocol.

- **What it would show:** whether covenants of unreported instruments are as observable as those of reported ones. This is the first measure here that is not conditioned on a breach.
- **What it would not show:** how common breaches are. Table 3 covers only monitored issues of reviewed trustees.

### 4. Longitudinal capture

Capture each trustee's and issuer's disclosure pages every quarter. Hash every file, record removals and replacements, and never overwrite. Where archives such as the Internet Archive hold earlier captures and their terms allow, use them to look backwards.

- **What it would show:** how often disclosures are silently revised (one Axis report already shows a waiver appearing between versions) and how long they stay available.

### 5. A note on the semantics of Table 5

Extend the date-column analysis to every trustee with a public report. Document how each uses "date of actual breach", carried-over rows and "further action". SEBI constituted an expert working group to review the trustee framework in June 2026, and invited suggestions until 15 July 2026 (`expert-working-group-suggestions`). That window has closed, so this would be a public research note, not a submission.

### 6. Later: an evaluation set for document understanding

Only after two people have annotated the same records independently and agreement has been measured. Candidate tasks follow from real difficulties in this corpus:

- recovering tables from files whose text is drawn as outlines or scanned;
- extracting exception lines from issuers' covenant statements;
- detecting when two statements of one covenant disagree.

Rows from sources that reserve AI-training rights must be excluded, and quotation rights reviewed.

## What not to do

- Do not assemble a contract corpus by getting around exchanges' controls. The finding that contracts are browser-public but closed to declared programs is itself the result, and it would be invalidated by working around it.
- Do not estimate breach prevalence, or rank issuers or trustees. Nothing in the sampling supports it.
- Do not build a bond directory, price feed or rating tracker. Those exist.
- Do not publish a single transparency score.
- Do not put model-generated readings of legal text into the dataset as if they were sources.

## What a recognisable contribution would look like

- **A data descriptor:** the dataset, its datasheet, the hash-verifiable evidence and the access log, published with a citable release.
- **A methods paper on measuring the observability of mandated disclosures:** India's corporate bond market as the case, with channels kept separate and absence never read as compliance.
- **A research note on trustee report semantics**, aimed at regulators and trustees.
- **Later, an evaluation set**, if annotation quality and rights allow.

Novelty has been assessed only against logged searches. The project should keep claiming no firsts.

## Connections to existing work

- **Covenants as contracts, and how researchers have measured them.** Smith and Warner (1979, *Journal of Financial Economics*) set out the theory of bond covenants. Most empirical work since has relied on purpose-built infrastructure. Dichev and Skinner (2002, *Journal of Accounting Research*) used a loan database. Billett, King and Mauer (2007, *Journal of Finance*) and Reisel (2014, *Journal of Corporate Finance*) used a bond-issue database with covenant fields. Chava and Roberts (2008, *Journal of Finance*), Roberts and Sufi (2009, *Journal of Finance*) and Nini, Smith and Sufi (2012, *Review of Financial Studies*) found covenant violations by searching regulatory filings. The Indian channels described above are the nearest public analogue of that infrastructure, and this project measures how far they go.
- **What summaries lose.** Ivashina and Vallée (2020, NBER Working Paper 27316) show that the carve-outs in loan contracts can matter as much as the headline covenant. A trustee's one-line description of a breach is a summary of exactly this kind.
- **Public is not the same as accessible.** Blankespoor, deHaan and Marinovic (2020, *Journal of Accounting and Economics*) review evidence that the cost of processing disclosures shapes who uses them. The access log here measures one such cost directly.
- **Data stewardship.** The FAIR principles (Wilkinson et al., 2016, *Scientific Data*) and datasheets for datasets (Gebru et al., 2021, *Communications of the ACM*) give a vocabulary for the dataset's own documentation.
- **Contract datasets in machine learning.** CUAD (Hendrycks et al., 2021), LEDGAR (Tuggener et al., 2020) and ContractNLI (Koreeda and Manning, 2021) are built from contracts filed with the US SEC. EDGAR publishes a policy for declared programmatic access, so the absence of comparable Indian resources may owe as much to access regimes as to the documents themselves.
- **Disclosure infrastructure elsewhere.** The EU's European single access point (Regulation (EU) 2023/2859) is designed to give centralised, machine-readable access to public financial disclosures. It is a policy contrast for the access findings here, not a model this project can adopt.
