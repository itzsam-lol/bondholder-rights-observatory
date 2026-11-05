# Formal access to exchange data: an assessment

Assessed on 4 November 2026 and re-checked on 5 November 2026 against the official texts named below. No exchange, depository, platform or regulator has been contacted, nothing has been applied for, and no term has been accepted. Each document was read once, as a reader would read a policy, and none of its content enters the dataset. NSE's documents are cited by title and date, without links, for the reasons given under [NSE's website terms](#nses-website-terms).

This is the project's reading of published policies, not legal advice.

## Why the question matters

Four things the dataset lacks are held by the exchanges:

1. **Visibility for large issuers.** In the pilot for the comparison sample, the June 2026 filings of three of four sampled issuers, including Power Finance Corporation and LIC Housing Finance, surfaced only on NSE (`cs-sample-*` in `data/searches.yaml`). The breach-selected sample's statements came from small issuers' own sites. Four issuers cannot show how general this is.
2. **The contract.** The trace from a reported breach to its contract stops at documents hosted on BSE or bond platforms (`contract_document` searches). Issuers file offer documents with the exchanges, and BSE hosts some trust deeds.
3. **When things became public.** Every availability date in the dataset is an estimate from a server's Last-Modified header or a lower bound from a document's own date. An exchange's dissemination time would be a publisher's own record of publication.
4. **Trustees' reports through a second channel.** Trustees must "Furnish a status report on its website and to the Stock Exchange" (`trustee-status-report`). Reports that did not surface on two trustees' sites may exist on the exchanges.

## Six questions that must be kept apart

Being allowed to obtain data says nothing about being allowed to publish what is learned from it. Each route below is assessed against six separate questions:

1. **Research access.** May the project obtain the data at all, and through whom?
2. **Retention and internal use.** May it keep the data, and for how long?
3. **Publishing derived measurements.** May it publish aggregates computed from the data, such as the share of an issuer's filings that its own site also carries?
4. **Publishing source-linked annotations.** May it publish ISIN-level records that cite a particular filing, with dates, levels, parties and short quotations?
5. **Redistributing source documents.** May it publish copies of the files?
6. **Unrestricted reuse under the project's licence.** May the records it derives be released under CC BY 4.0 for anyone to reuse?

| Question | Exchanges' research route | Exchanges' public websites | Depositories' research route | Bond Central |
|---|---|---|---|---|
| 1. Access | Only through "accredited academic institutions, recognized research organizations and think tanks", not for "commercial, speculative, or investigative purposes", with a request justifying the data "to test the specific hypothesis" | Filings can be viewed. BSE refused the project's declared program on 4 November 2026. The project excludes NSE by its own policy | A request form signed by the institution, and an undertaking or NDA | A free public site. No terms were found |
| 2. Retention | Not stated. An NDA "may" be required even for free data, and its terms are unknown | Governed by each site's terms. The project keeps hashes, not files | Data must be purged "On Completion of Duration of project" | Unknown |
| 3. Derived measurements | Not stated | The project publishes facts with citations. Whether the sites' terms permit it is an open legal question ([legal-review-brief.md](legal-review-brief.md)) | Not stated | Unknown |
| 4. Source-linked annotations | Not stated. Per-issuer records could be read as "investigative" | BSE filings may be cited by link. NSE filings would be cited without links | Not stated. The project cites single values seen on CDSL's public pages by link | Links are within the project's policy for the site. Its terms are unknown |
| 5. Redistributing documents | Not stated | BSE's disclaimer prohibits reproduction or redistribution. The project redistributes no source file from any host | Issuers' "contract" information is in the non-shareable basket. CDSL's site forbids copying, downloading or storage without permission | Unknown |
| 6. Reuse under CC BY 4.0 | Only if an agreement expressly allows it | The licence covers only the project's own contributions. Quotations, titles and names are excluded ([LICENSE-DATA.md](../LICENSE-DATA.md)) | Only if an agreement expressly allows it | As for public websites |

Nothing read answers questions 2 to 6 for the research routes. The research routes govern access, and the policies are silent on what may be published.

## What the rules provide

### SEBI, 20 December 2024: data for academic research

Circular SEBI/HO/DEPA-II/DEPA-II_SRG/P/CIR/2024/178, "Policy for Sharing Data for the Purpose of Research / Analysis", was read from SEBI's official PDF on 4 November 2026 and again on 5 November 2026.

- **Who.** Exchanges, clearing corporations and depositories are to share data "for only research/ research publications undertaken by accredited academic institutions". Data sold to vendors falls outside the policy. The circular does not define accreditation.
- **What.** Each institution sorts its data into two baskets. The first holds data that "can be shared with the public", which "should be aggregate and analysed data only" and "shall also include reporting and disclosure data that are mandated by the regulators". It has two parts: data already "publicly available on respective website" (paragraph 3.1.1), and data "which is voluminous and cannot be placed on the respective websites" (paragraph 3.1.2). The second basket holds what cannot be shared, such as KYC data, trade logs, holdings and "Confidential information of DPs, RTAs, Issuers etc."
- **Cost.** The free allowance is conditional. Paragraph 3.1.2 says the institutions "would provide a reasonable amount of data requested by a researcher free of cost (upto 2 GB of data per researcher per year that requires no extra computation)", and that if the data "is very high in volume and/ or needs further processing/ value addition", they "may charge a cost-basis fee". So 2 GB is a ceiling on free provision, not an entitlement. It applies to the voluminous part of the first basket, to an amount the institution judges reasonable, and only to data that needs no extra computation. Extracting the filings of entities that list only debt, with their attachments and timestamps, may well count as processing; the circular does not say.
- **How.** A data seeking request form in which "the data seeker shall justify as to how the particular data sought is necessary for his/her/its/their research project to test the specific hypothesis".
- **Not stated.** Publication, citation, onward sharing and retention are left to each institution's policy.

### The exchanges' uniform policy

"Uniform Data Sharing Policy by Exchanges for Research Purposes and Analysis", version 1.0 of 27 June 2025, was read as NCDEX publishes it, as an annexure to its data feed policy. NCDEX's research page adds that "All requests for data shall be submitted only though accredited academic institutions / research institutions". NSE's data list for research, dated 28 July 2025, matches the annexure item for item. Neither NSE's nor BSE's own copy of the policy text was found, so treat the terms below as the common template, not as either exchange's confirmed terms.

| Term | What the policy says |
|---|---|
| Scope | "not only market trading data but also corporate disclosures and filings", in every segment including debt |
| Eligibility | "restricted to individuals from accredited academic institutions, recognized research organizations and think tanks" |
| Excluded | "Data requests for research for commercial, speculative, or investigative purposes" |
| Free data (up to 2 GB) | "may require execution of a binding Non-Disclosure Agreement (NDA) between the researcher, researcher's parent institution and the Exchanges" |
| Voluminous data | Chargeable, needs a binding NDA, and "will have a vintage of six month from the date of the request". This probably means that the data supplied will be at least six months old. The policy does not say |
| Review | Exchanges may refuse, with written reasons. Recipients of customised or extensive datasets report their usage periodically, and access can be ended for breach of the NDA |
| Not stated | Whether results or derived data may be published, citation, retention or purging, and redistribution |

### NSE: which category would hold what the project needs

NSE's "Data list under NSE Data Sharing Policy for Research and Analysis" (28 July 2025) puts these in the first basket under "Listed Companies' Data": "Corporate Announcements", "Offer Documents", and "Information disseminated on exchange website in compliance with SEBI Regulations". Among chargeable voluminous data it lists "Corporate Data (for eg. company fundamentals, corporate announcements, shareholding pattern, ...)".

| What the project needs | Closest item | Basket | What the list does not say |
|---|---|---|---|
| Individual debt filings, as disseminated | "Corporate Announcements"; "Information disseminated on exchange website in compliance with SEBI Regulations" | First, as data already on the website | Whether entities that list only debt are covered |
| A historical extract of those filings, in bulk | "Corporate Data (for eg. ... corporate announcements ...)" | Voluminous and chargeable, so a binding NDA and the six-month vintage apply | Whether PDF attachments are included, and how far back debt filings go |
| Offer documents | "Offer Documents" | First | Whether key information documents of private placements, and trust deeds, are included |
| When each filing was disseminated | No item names it | None | Whether announcement data carries receipt or dissemination times |

On this reading the project's need is closest to voluminous corporate data: chargeable, under an NDA, and probably at least six months old. Viewing individual announcements on the website is a different thing from receiving them in bulk. NSE's research page says data "is strictly limited to academic and non-commercial use". Its request form, dated 19 March 2025, asks for the institution, the project's title and objective, the type of data, a justification and a period.

### BSE

BSE's market data page, viewed on 4 November 2026, links SEBI's circular and a "Data seeking request form for the Purpose of Research / Analysis". It sells corporate data commercially, including announcements, under a tariff dated February 2025. It offers "Historical Corporate data (Results, Shareholding pattern and Corporate actions)" since 2006. It does not say whether announcements by entities that list only debt are covered.

### Depositories: no route to the covenant system

The depositories' list (NSDL's copy, published in April 2026 and stated to be uniform across depositories) offers "List of Issuers and ISINs" in its shareable basket. It puts issuers' "contract" information in the non-shareable basket. It lists nothing from the Security and Covenant Monitoring System, the depository system in which trust deeds and covenants are recorded (chapter III of SEBI's master circular for debenture trustees, SEBI/HO/DDHS-PoD-1/P/CIR/2025/117 of 13 August 2025). The project therefore does not assume that the system's data can be had through the research route. NSDL's guidelines require:

- a request form signed by the institution;
- an undertaking or NDA;
- that "On Completion of Duration of project, Data Seeker needs to purge the data".

CDSL's public Corporate Bond Database pages, which the project consults by hand, have columns per exchange listing headed "Term Sheet", "Annual Report", "Allotment Confirmation Letter", "Shelf Prospectus", "Information Memorandum" and "Offer Documents". In two pages for one issuer seen in search excerpts on 5 November 2026, those columns were empty. How often the database holds documents is unknown.

### Bond Central

The project's network still cannot reach Bond Central. Its home page, search page and "About" page were read through a third-party reading service on 5 November 2026.

- **Origin.** The home page gives totals (707 issuers, 6,900 ISINs) under the label "Source: NSE, BSE, NSDL, CDSL and CCIL as of Jan, 2026". If the label is current, the figures were about ten months old when read.
- **What is visible.** The search page lists issuer name, ISIN, coupon, maturity and rating, with a "View Details" link for each ISIN. No detail page could be read.
- **Documents, history and timestamps.** Unknown. SEBI's press release says the site offers "corporate bond documents, and disclosures" (`bond-central-documents`). Nothing read on the site confirmed that, or showed whether documents are identified by title and date, whether earlier versions are kept, or whether times are shown.
- **Terms.** The "About" page returned no text. No terms of use or disclaimer was found.

A person needs to open the site in a browser on another network, read its terms, and record what a detail page shows for a few of the dataset's ISINs. A second search later on 5 November 2026 found the same three pages and still no terms, disclaimer or per-ISIN page.

### SEBI, 25 February 2022: free use of mandated disclosures

Circular SEBI/HO/DEPA-III/DEPA-III_SSU/P/CIR/2022/25, "Approach to securities market data access and terms of usage of data provided by data sources in Indian securities market", is addressed to exchanges, depositories, credit rating agencies and debenture trustees, among others. Paragraph 4 says:

> "As far as the data provided by various data sources in Indian securities markets pursuant to regulatory mandates for reporting and disclosure in public domain are concerned, such data should be made available to users, 'free of charge' both for 'viewing' the data as also for download in the format as specified by regulatory mandate for reporting, as well as their usage for the value addition purposes."

**Its current status, checked on 5 November 2026 against SEBI's own documents.** The circular has been rescinded only in part. Master circulars for particular intermediaries reproduce paragraph 4 for them and rescind earlier circulars "to the extent they relate to" those intermediaries:

- for registrars and share transfer agents, SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/91 of 23 June 2025, item 37;
- for investment advisers, SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/94 of 27 June 2025, paragraph 17.1, which reproduces paragraph 4 word for word.

The custodians' master circular of April 2023 instead tells custodians to "independently comply" with it. SEBI's research circular of 20 December 2024 opens by citing it. This check found no master circular that rescinds it for stock exchanges, depositories or debenture trustees. The master circulars for stock exchanges and for depositories were not examined, and the one for debenture trustees only by its table of contents, which has no chapter on it. The secondary index that described it as subsumed into the registrars' master circular was describing a partial rescission. The wording of paragraph 4 is now confirmed from a text SEBI hosts, not only from reproductions.

It speaks to charging and to "usage for the value addition purposes". It does not mention automated retrieval or linking, and it does not settle whether a website's restrictive terms are consistent with it. That is a question for legal review ([legal-review-brief.md](legal-review-brief.md)). The project's quotation limits and access rules are unchanged.

### SEBI's own data

SEBI's guidelines for seeking its data share only "historical, anonymized" data at least two years old, under an undertaking of confidentiality. The source must be acknowledged in published work, and data must be expunged when the project ends. Anonymised data could not support an instrument-level record.

### NSE's website terms

NSE's "Terms of Use" (updated 29 October 2025) bind users of the site to a set of policies that includes its copyright and hyperlinking policies. On 5 November 2026 the reading service did not return items 6 to 16 of the terms, and returned the copyright policy (updated 21 October 2025) with no text. The hyperlinking policy (updated 21 October 2025), as returned, says only that NSE's own links to third-party sites are for users' convenience. It says nothing about others linking to NSE.

That does not match the project's source record for NSE, read on 3 November 2026. The record says the hyperlinking policy "requires prior written permission before third-party sites link to NSE". It also quotes a prohibition of "any systematic or automated data collection activities (including scraping, data mining, data extraction and data harvesting)". That wording matches item 8.7 of the terms of FixedIn word for word. FixedIn is a bond-data platform run by NSE Data, which the project does not use. Whether NSE's main terms carry the same clause could not be confirmed, because those items were not returned.

Both readings came through services that render script-driven pages imperfectly, so neither settles the matter. The project keeps NSE excluded and unlinked until a person reads the three pages in a browser and records what they say. A rule should not be relaxed on the strength of a partial reading.

## What formal access could change

| Dimension | Likely effect | Why |
|---|---|---|
| Visibility | **Large.** Could show which debt filings exist for issuers whose own pages do not link them | Corporate announcements are in the first basket. Whether bulk data covers debt-only issuers and their attachments is not stated |
| Contract trace | **Possible.** Offer documents are listed | Whether key information documents of private placements and trust deeds are included is not stated. Neither would be an executed deed unless the exchange holds one |
| Timing | **Large, if timestamps are included.** Dissemination times would replace Last-Modified estimates | The lists do not say whether announcement timestamps are provided |
| History | **Some.** Archives extend back years | Voluminous data probably has a six-month vintage, and the depth of debt filings is unknown |
| Reproducibility for others | **Worse, unless the terms allow publication.** Only eligible researchers could obtain the same data, under their own NDA | No route gives the public what the dataset would rest on |
| Openness of the published records | **At risk.** An NDA may forbid publishing instrument-level facts drawn from the data, and per-issuer records could be read as "investigative" | The policy is silent on publication and excludes investigative use |

## Assessment

Formal access is worth pursuing for what the open record cannot do:

- measure what open channels miss, for example the share of an issuer's mandated debt filings that its own site or its trustee's site also carries (question 3);
- date disclosures by the exchange's own dissemination record, if the data includes it.

On the published terms it is not a way to build the public dataset, because access (question 1) is the only question the research policies answer. Facts that only NDA data could supply would have to stay out of the published records unless the agreement expressly permits publishing them at ISIN level with a citation (questions 4 and 6). If access is obtained, keep it as a separate, restricted tier: never mixed into `data/`, labelled by licence, retained only as the agreement allows (question 2), and published only as aggregates the agreement allows.

Open routes come first:

1. **Bond Central.** SEBI describes it as an "information repository for the public at large" with "corporate bond documents, and disclosures" (`bond-central-scope`, `bond-central-documents`). What the site shows per ISIN, and its terms, are still unknown (above). If it holds offer documents and disclosures under terms that allow citation, it could close more of the gap than any agreement.
2. **Manual retrieval of the BSE candidates**, under the existing manual-only policy ([coverage.md](coverage.md)). What each candidate could establish depends on its legal stage, which coverage.md sets out.
3. **Issuers' own regulation 62 pages, searched systematically**, since regulation 62(1)(g) requires them to carry the compliance reports the issuer files.

## Questions to settle before any application

These are for the project owner to put, through the academic institution, if and when they choose to. Nothing has been sent.

**Access and retention**

1. Does a continuing public dataset on disclosure practice count as research rather than "investigative" use?
2. Must data be purged when the project ends? May hashes, and records derived from the data, be kept?

**Publication and licence**

3. May aggregate measurements derived from the data be published?
4. May derived facts be published at ISIN level, meaning dates, levels, parties and the existence of a filing, with short quotations and a citation by exchange, filing date and time, and subject?
5. May such records be released under CC BY 4.0, or only under the agreement's own terms?
6. The project does not intend to publish supplied files. May it publish their hashes, so that others can confirm they hold the same file?

**Coverage**

7. Does "Corporate Announcements" bulk data cover entities that list only debt, with their PDF attachments? Does it include dissemination timestamps?
8. Are debt offer documents, including key information documents of private placements, and trust deeds filed with the exchange included?
9. What does the six-month vintage mean for corporate data, and how far back do debt filings go? Would a debt-only subset count as needing "extra computation"?

**Linking and retrieval**

10. For NSE: may individual filings be linked or cited in a public dataset? This depends on what its hyperlinking policy and terms actually say (above).
11. For BSE: may a declared program retrieve individually cited documents, such as offer documents and trust deeds, at a polite rate? BSE refused the project's identified client on 4 November 2026.

## Sources read

| Document | Where it was read | Checked |
|---|---|---|
| SEBI circular SEBI/HO/DEPA-II/DEPA-II_SRG/P/CIR/2024/178, 20 December 2024 | [SEBI's PDF](https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1734693561713.pdf) | 2026-11-04, 2026-11-05 |
| SEBI circular SEBI/HO/DEPA-III/DEPA-III_SSU/P/CIR/2022/25, 25 February 2022 | [SEBI's page](https://www.sebi.gov.in/legal/circulars/feb-2022/approach-to-securities-market-data-access-and-terms-of-usage-of-data-provided-by-data-sources-in-indian-securities-market_56420.html), text from reproductions | 2026-11-04 |
| Master Circular for Registrars to an Issue and Share Transfer Agents, SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/91, 23 June 2025 | [SEBI's PDF](https://www.sebi.gov.in/sebi_data/attachdocs/jun-2025/1750678372996.pdf), from search excerpts | 2026-11-05 |
| Master Circular for Investment Advisers, SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/94, 27 June 2025 | [SEBI's PDF](https://www.sebi.gov.in/sebi_data/attachdocs/jun-2025/1751022988074.pdf), from search excerpts | 2026-11-05 |
| Master Circular for Custodians, April 2023 | [SEBI's PDF](https://www.sebi.gov.in/sebi_data/attachdocs/apr-2023/1682590624880.pdf), from search excerpts | 2026-11-05 |
| Master Circular for Debenture Trustees, SEBI/HO/DDHS-PoD-1/P/CIR/2025/117, 13 August 2025 | [SEBI's PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2025/1755087354414.pdf), table of contents only | 2026-11-05 |
| Uniform Data Sharing Policy by Exchanges for Research Purposes and Analysis, v1.0, 27 June 2025 | [NCDEX's copy](https://www.ncdex.com/downloads/Others%202026/Data%20Feed%20policy/Annexure%202_Exchange%20Data%20Sharing%20Poilcy%20for%20Reseach.pdf) | 2026-11-04 |
| Data list under NSE Data Sharing Policy for Research and Analysis, 28 July 2025; NSE's "Data for Research" page; Data Seeking Request Form, 19 March 2025 | NSE's website (not linked) | 2026-11-04 |
| NSE Terms of Use, 29 October 2025; NSE Hyperlinking Policy and Copyright Policy, 21 October 2025; NSE Data's FixedIn Terms of Use | NSE's websites (not linked), items 6 to 16 of the terms and the copyright text not returned | 2026-11-05 |
| BSE market data products page; BSE Information Products Tariff, February 2025 | [BSE's page](https://www.bseindia.com/market_data_products.html?flag=eod) | 2026-11-04 |
| Data List for Depositories; NSDL Guidelines to Seek Data | [NSDL's list](https://nsdl.com/nsdl/2026-04/Policy%20for%20Sharing%20Data%20for%20the%20Purpose%20of%20Research%20%20Analysis%20Data%20List%20for%20Depositories.pdf), [NSDL's guidelines](https://nsdl.com/nsdl/2026-04/Guidelines%20to%20Seek%20Data.pdf) | 2026-11-04 |
| CDSL Corporate Bond Database, two pages for one issuer | Search excerpts | 2026-11-05 |
| Bond Central home, search and "About" pages | [bondcentral.in](https://bondcentral.in/) | 2026-11-05 |
| SEBI Guidelines for Seeking Data | [SEBI's PDF](https://www.sebi.gov.in/pdf/guidelines-of-data-sharing-final.pdf) | 2026-11-04, from a search excerpt only |

These were read through third-party reading and search services, because this project's network could not reach the hosts. Search excerpts are partial, and pages built by scripts may be returned incompletely. None of these documents is registered as a document in `data/`, because none is evidence for a record. The checked dates are for this assessment only.
