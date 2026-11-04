# Coverage: what the record holds, what it misses, and why

Written on 4 November 2026 from the records in `data/`. Figures are recomputed by `brdo report`, and the issuer counts come from the same records. This describes the sample, not the market.

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
| Meetings adjourned for lack of quorum | 15 | 3 |
| Holders instructed no action | 6 | 3 |
| Agreements between an issuer's statement and a trustee's report | 17 | 2 (Dvara 11, Satya 6) |
| The issuer prints its measured level and the trustee does not | 8 | 1 (Dvara, in Catalyst's report) |
| Comparisons between statements and reports, in all | 22 | 3 |

The report now prints the number of issuers beside every ISIN count in these tables. A finding about "nine cases" that rests on one issuer and two trustees is a well-documented case, not a pattern.

## Channels the record can and cannot see

| Channel | Used | What it shows |
|---|---|---|
| Trustees' websites | Every breach report, census and letter | Only trustees whose sites the project reviewed, and only what each chooses to publish beyond the prescribed tables |
| Issuers' own websites | 3 issuers' statements for the quarter, all small lenders | Large issuers' filings may be visible mainly through exchanges; in the pilot, 3 of 4 sampled issuers' filings surfaced only on NSE |
| Exchanges | None. BSE is manual-only and NSE excluded | Offer documents, trust deeds hosted by BSE, issuers' debt filings, exchange approvals, dissemination times |
| Rating agencies | 1 rationale | Covenant statements are mandated only for credit-enhanced and structured ratings |
| Depositories | Single values, cited by link | No covenant data is public |
| Bond Central | Not assessed; unreachable | Described by SEBI as a public repository of bond documents and disclosures |
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

| Gap | Instruments | What it would add | What it would not | Priority |
|---|---|---|---|---|
| Pahal's two filings for the June 2026 quarter, refused to the project's client (HTTP 403) | 7 ISINs, all listed by Catalyst | Probably the issuer's covenant statement. That would add up to 7 comparisons and a fourth issuer to the issuer–trustee comparison, which now rests on 3 issuers, and a third to the field-level analysis, which rests on 2 | Whether either file holds a covenant statement is unknown until opened | **First.** Two files, and the largest gain in independent cases |
| Aye Finance's key information document on BSE, naming INE501X07570 | 1 | The first offer-document text in the dataset, so the trustee's quotation of clause 9.3(a)(viii) could be compared with the document it comes from | The executed deed, or later amendments | High |
| Satya's general information document on BSE, and an issue document named for INE982X08091 on a bond platform | 1 or more | A check of the trustee's quotation of clause 9.3 for an issuer central to the comparisons | The platform's terms forbid extraction tools and derivative databases, so the platform copy waits for legal review | High for the BSE copy |
| A 2013 trust deed for Meghalaya Energy on BSE | Unknown | Possibly the first executed contract text | It has not been opened, so whether it governs any listed ISIN is unknown | Medium |
| Akara's general information document on BSE | 1 | Programme-level terms | Not the instrument's own key information document | Low |
| Issue documents offered by a bond platform for Ramasigns and Watermarke | 2 | Offer-document text | The platform's terms forbid derivative databases | Hold until legal review |
| SBICAP's and Orbis's reports for the quarter | Unknown | The two missing trustees | Orbis reserves AI-training rights | Medium; also check the exchanges' copies |
| 18 registered trustees not reviewed | Unknown | Breadth | — | After the above |
| Bond Central | Unknown | Possibly documents and disclosures for every ISIN | Its terms are unknown | **First among sources** (see [exchange-access.md](exchange-access.md)) |

**Overall significance.** Closing every BSE gap would give at most four instruments some contract text, against 93 listed ISINs. That would not change the headline that the contract is almost never in the public trail an automated, declared process can follow. But it would make the fidelity question testable for the first time: does the trustee quote what the document says? Pahal's two filings matter more for the dependence findings, because they would add an issuer to a comparison that now rests on two or three.

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
