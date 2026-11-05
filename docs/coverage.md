# Coverage: what the record holds, what it misses, and why

Written on 4 November 2026 from the records in `data/`, and revised on 5 November 2026. Figures are recomputed by `brdo report`, and the issuer counts come from the same records. This describes the sample, not the market.

## The sample is clustered, not just selected

The sample starts from instruments that trustees listed for a breach, so it says nothing about how common breaches are (see [research-design.md](research-design.md)). It is also concentrated in ways that ISIN-level counts hide.

- **By trustee.** Of the 91 ISINs listed in the current reports for the quarter ended 30 June 2026, Catalyst lists 44 and IDBI 38. Vistra lists 7, and Axis and MITCON one each. SEBI's register named 26 trustees; reports were sought from 8 and found for 6.
- **By issuer.** The 91 ISINs belong to 28 issuers, and five of them hold 48:
  - National Highways Authority of India, 15;
  - Dvara KGFS, 11;
  - Meghalaya Energy Corporation, 8;
  - Punjab Infrastructure Development Board, 7;
  - Pahal Financial Services, 7.
- **By kind of issuer,** on the project's reading of their names (not a recorded field): eleven issuer records are lenders, mostly microfinance and other non-bank lenders, and four are public bodies.

**One issuer's ISINs share one history.** The same deed, the same certificate and the same trustee letter usually apply to all of them, so twenty ISINs of one issuer are closer to one observation than to twenty. The fourth pass's findings rest on very few issuers:

| Finding | ISINs | Issuers |
|---|---|---|
| Cures published, all of late filings or similar obligations | 24 | 3; NHAI accounts for 15 ISINs and Meghalaya Energy for 8 |
| Meetings adjourned for lack of quorum | 14 | 3 |
| Holders instructed no action | 6 | 3 |
| Agreements between an issuer's statement and a trustee's report | 17 | 2 (Dvara 11, Satya 6) |
| The issuer prints its measured level and the trustee does not | 8 | 1 (Dvara, in Catalyst's report) |
| Comparisons between statements and reports, in all | 22 | 3 |

The report now prints the number of issuers beside every ISIN count in these tables. A finding about "nine cases" that rests on one issuer and two trustees is a well-documented case, not a pattern.

## Populations, kept apart

Several analyses use different sets of ISINs. They overlap but are not the same, and a figure from one does not describe another:

| Population | ISINs | Issuers | Trustees | What it is |
|---|---|---|---|---|
| Listed for breach, quarter ended 30 June 2026 | 91 | 28 | 5 | Every ISIN in the current reviewed breach reports for the quarter |
| Statement and report compared | 22 comparisons of 20 ISINs | 3 | 2 | An issuer's or auditor's statement for the quarter set beside the trustee's report. Two ISINs are compared twice, against two statements |
| Agreements among them | 17 | 2 | 2 | The comparisons that agree. Only these enter "What each party adds" (`field_flows.csv`) |
| Comparison sample | 20 | 19 issuer codes | 1 | ISINs in Catalyst's census that its breach report does not list, drawn by a fixed rule as a contrast to the breach-listed sample |
| Comparison-sample pilot | 4 | 4 | 1 | The sampled ISINs searched so far for an issuer's statement: Power Finance Corporation, LIC Housing Finance, Shriram Finance and Godrej Finance. None was found on a source the pipeline may use |

The sample's issuers are counted by the issuer code in their ISINs, because no issuer record is kept for them.

## Channels the record can and cannot see

| Channel | Used | What it shows |
|---|---|---|
| Trustees' websites | Every breach report, census and letter | Only trustees whose sites the project reviewed, and only what each chooses to publish beyond the prescribed tables |
| Issuers' own websites | 3 issuers' statements for the quarter, all small lenders | Large issuers' filings may be visible mainly through exchanges; in the pilot, 3 of 4 sampled issuers' filings surfaced only on NSE |
| Exchanges | None. BSE is manual-only and NSE excluded | Offer documents, trust deeds hosted by BSE, issuers' debt filings, exchange approvals, dissemination times |
| Rating agencies | 1 rationale | Covenant statements are mandated only for credit-enhanced and structured ratings |
| Depositories | Single values, cited by link | No covenant data is public |
| Bond Central | Home and search pages only, read through a reading service on 5 November 2026; no per-ISIN page or terms | Described by SEBI as a public repository of bond documents and disclosures. Its totals were labelled "as of Jan, 2026" when read |
| Web search | 59 logged queries through one search tool | Results change over time; a `not_found` is not evidence of absence |

So the record over-represents:

- trustees that publish rich tables and letters (Catalyst prints clause text and publishes meeting letters);
- issuers that keep filings on their own sites.

It under-represents large issuers, whose filings may run through the exchanges, and every document hosted only by an exchange. Comparisons across trustees, or between small and large issuers, would mostly measure these channel differences.

## Time

Almost everything concerns one quarter, ended 30 June 2026, captured on 3 and 4 November 2026. No earlier state of any page was captured. Availability dates before November rest on servers' Last-Modified headers, and `--availability observed` shows that the project itself saw nothing before 3 November 2026.

Catalyst's page of census tables lists a file for every quarter back to June 2024, which allows a lawful look backwards that has not yet been taken.

## Document gaps, and what closing each would change

No candidate below has been retrieved. Each needs a person to download it in an ordinary browser and ingest it with `brdo add-document --from-file`, which records `retrieved_manually: true` and the file's hash. Nothing may be done to get round a refusal.

What a document can establish depends on its legal stage, and the stages are not interchangeable:

| Stage | Document | Establishes | Does not establish |
|---|---|---|---|
| Offered | General or key information document, placement memorandum | The terms on which the debentures were offered | That the deed was executed on those terms, or that they were not amended later |
| Proposed | A notice or filing putting forward a change, such as a revised schedule of covenants | That a change was proposed | That it was approved or made |
| Approved | An approval required before a change, such as an exchange's under regulation 59 | That the change was approved | That a supplemental deed was executed, or when it took effect |
| Executed | A signed debenture trust deed or supplemental deed | The operative terms as executed | Later amendments, unless every supplemental deed is held; whether an unsigned or partial copy is the executed text |
| Described | A trustee's or issuer's quotation or description of a term | What that party says the term is | What the contract says. Comparing the two is the fidelity question |

None of the candidates below is a proposed change or an approval. Four are offer documents and one may be an executed deed.

| Gap | Stage | Instruments | What it would add | What it would not | Priority |
|---|---|---|---|---|---|
| Pahal's two filings for the June 2026 quarter, refused to the project's client (HTTP 403) | Not a contract document: an issuer's filing | 7 ISINs, all listed by Catalyst | Probably the issuer's covenant statement. That would add up to 7 comparisons and a fourth issuer to the issuer–trustee comparison, which now rests on 3 issuers, and a third to the field-level analysis, which rests on 2 | Whether either file holds a covenant statement is unknown until opened | **First.** Two files, and the largest gain in independent cases |
| Aye Finance's key information document on BSE, naming INE501X07570 | Offered | 1 | The first offer-document text in the dataset: the terms as offered, against which the trustee's quotation of clause 9.3(a)(viii) could be compared | The executed deed, whose numbering may differ, or later amendments | High |
| Satya's general information document on BSE, and an issue document named for INE982X08091 on a bond platform | Offered | 1 or more | A check of the trustee's quotation of clause 9.3 for an issuer central to the comparisons | The platform's terms forbid extraction tools and derivative databases, so the platform copy waits for legal review | High for the BSE copy |
| A 2013 trust deed for Meghalaya Energy on BSE | Executed, if the copy is signed and complete | Unknown | Possibly the first executed contract text | It has not been opened, so whether it is the signed deed, whether it governs any listed ISIN, and what supplemental deeds followed are unknown | Medium |
| Akara's general information document on BSE | Offered, at programme level | 1 | Programme-level terms | Not the instrument's own key information document | Low |
| Issue documents offered by a bond platform for Ramasigns and Watermarke | Offered | 2 | Offer-document text | The platform's terms forbid derivative databases | Hold until legal review |
| SBICAP's and Orbis's reports for the quarter | Not a contract document | Unknown | The two missing trustees | Orbis reserves AI-training rights | Medium; also check the exchanges' copies |
| 18 registered trustees not reviewed | — | Unknown | Breadth | — | After the above |
| Bond Central | Unknown | Unknown | Possibly documents and disclosures for every ISIN | Its terms are unknown | **First among sources** (see [exchange-access.md](exchange-access.md)) |

**Overall significance.** Closing every BSE gap would give at most four instruments some offer-document text, and perhaps one executed deed, against 93 listed ISINs. That would not change the headline that the contract is almost never in the public trail an automated, declared process can follow. But it would make the fidelity question testable for the first time: does the trustee quote what the document says? Pahal's two filings matter more for the dependence findings, because they would add an issuer to a comparison that now rests on two or three.

## What a user can conclude

- That a trustee, issuer or auditor published a particular statement, when the record says so and cites the page.
- How far the reviewed public trail reaches for the instruments in the sample, and where it stops.
- How two publications describing the same instrument and quarter differ.

## What a user cannot conclude

- How often breaches occur, or whether any issuer complied.
- Anything about trustees, issuers or channels not reviewed.
- That ISIN counts are independent observations.
- That a missing record means a missing disclosure: absence can mean not published, not found, not reachable, not yet captured or excluded by policy, and `instrument_status.basis` and `searches.csv` say which.
- When something was first public, beyond the bounds that `documents.csv` gives.
