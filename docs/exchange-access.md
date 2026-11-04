# Formal access to exchange data: an assessment

Assessed on 4 November 2026 from the official texts named below. No exchange, depository or regulator has been contacted, nothing has been applied for, and no term has been accepted. Each document was read once, as a reader would read a policy, and none of its content enters the dataset. Under NSE's hyperlinking policy, NSE's documents are cited here by title and date, without links.

This is the project's reading of published policies, not legal advice.

## Why the question matters

Four things the dataset lacks are held by the exchanges:

1. **Visibility for large issuers.** In the pilot for the comparison sample, the June 2026 filings of three of four sampled issuers, including Power Finance Corporation and LIC Housing Finance, surfaced only on NSE (`cs-sample-*` in `data/searches.yaml`). The breach-selected sample's statements came from small issuers' own sites. Four issuers cannot show how general this is.
2. **The contract.** The trace from a reported breach to its contract stops at documents hosted on BSE or bond platforms (`contract_document` searches). Issuers file offer documents with the exchanges, and BSE hosts some trust deeds.
3. **When things became public.** Every availability date in the dataset is a server's Last-Modified header or a document's own date. An exchange's dissemination time would be a publisher's own record of publication.
4. **Trustees' reports through a second channel.** Trustees must "Furnish a status report on its website and to the Stock Exchange" (`trustee-status-report`). Reports that did not surface on two trustees' sites may exist on the exchanges.

## What the rules provide

### SEBI, 25 February 2022: free use of mandated disclosures

Circular SEBI/HO/DEPA-III/DEPA-III_SSU/P/CIR/2022/25, "Approach to securities market data access and terms of usage of data provided by data sources in Indian securities market", is addressed to exchanges, depositories, credit rating agencies and debenture trustees, among others. Paragraph 4 says:

> "As far as the data provided by various data sources in Indian securities markets pursuant to regulatory mandates for reporting and disclosure in public domain are concerned, such data should be made available to users, 'free of charge' both for 'viewing' the data as also for download in the format as specified by regulatory mandate for reporting, as well as their usage for the value addition purposes."

The text was read from reproductions, a stock exchange's notice to its members and a law firm's copy, because SEBI's own page embeds the circular. One secondary index says the circular was later subsumed into a master circular. Its current form was not checked.

It speaks to charging and to "usage for the value addition purposes". It does not mention automated retrieval or linking, and it does not settle whether a website's restrictive terms are consistent with it. That is a question for legal review ([legal-review-brief.md](legal-review-brief.md)). The project's quotation limits and access rules are unchanged.

### SEBI, 20 December 2024: data for academic research

Circular SEBI/HO/DEPA-II/DEPA-II_SRG/P/CIR/2024/178, "Policy for Sharing Data for the Purpose of Research / Analysis", was read from SEBI's official PDF.

- **Who.** Exchanges, clearing corporations and depositories are to share data "for only research/ research publications undertaken by accredited academic institutions". Data sold to vendors falls outside the policy. The circular does not define accreditation.
- **What.** Each institution sorts its data into two baskets. The first "can be shared with the public" and "shall also include reporting and disclosure data that are mandated by the regulators". Its annexure gives "Disclosures required under Listing regulations" and a "Corporate Bonds Traded Report" as examples. The second holds what cannot be shared, such as KYC data, trade logs, holdings and "Confidential information of DPs, RTAs, Issuers etc."
- **Cost.** Up to 2 GB of first-basket data per researcher per year is free when it needs no extra computation. Larger or processed requests may carry a "cost-basis fee".
- **How.** A data seeking request form in which "the data seeker shall justify as to how the particular data sought is necessary for his/her/its/their research project to test the specific hypothesis".
- **Not stated.** Publication, citation, onward sharing and retention of the data are left to each institution's policy.

### The exchanges' uniform policy

"Uniform Data Sharing Policy by Exchanges for Research Purposes and Analysis", version 1.0 of 27 June 2025, was read as NCDEX publishes it, as an annexure to its data feed policy. NSE's data list for research, dated 28 July 2025, matches its annexure item for item. Neither NSE's nor BSE's own copy of the policy text was found, so treat the terms below as the common template, not as either exchange's confirmed terms.

| Term | What the policy says |
|---|---|
| Scope | "not only market trading data but also corporate disclosures and filings", in every segment including debt |
| Eligibility | "restricted to individuals from accredited academic institutions, recognized research organizations and think tanks" |
| Excluded | "Data requests for research for commercial, speculative, or investigative purposes" |
| Free data (up to 2 GB) | "may require execution of a binding Non-Disclosure Agreement (NDA) between the researcher, researcher's parent institution and the Exchanges" |
| Voluminous data | Chargeable, needs a binding NDA, and "will have a vintage of six month from the date of the request" |
| Review | Exchanges may refuse, with written reasons. Recipients of customised or extensive datasets report their usage periodically, and access can be ended for breach of the NDA |
| Not stated | Whether results or derived data may be published, citation, retention or purging, and redistribution |

**What the lists offer.** NSE's list, "Data list under NSE Data Sharing Policy for Research and Analysis" (28 July 2025), puts these in the freely available first basket under "Listed Companies' Data":

- "Corporate Announcements";
- "Offer Documents";
- "Information disseminated on exchange website in compliance with SEBI Regulations".

Among chargeable voluminous data it lists "Corporate Data (for eg. company fundamentals, corporate announcements, shareholding pattern, ...)". NSE's research page says data "is strictly limited to academic and non-commercial use". Its request form, dated 19 March 2025, asks for the institution, the project's title and objective, the type of data, a justification and a period.

**BSE.** BSE's market data page, viewed on 4 November 2026, links SEBI's circular and a "Data seeking request form for the Purpose of Research / Analysis". It sells corporate data commercially, including announcements, under a tariff dated February 2025. It offers "Historical Corporate data (Results, Shareholding pattern and Corporate actions)" since 2006. It does not say whether announcements by entities that list only debt are covered.

### Depositories: no route to the covenant system

The depositories' list (NSDL's copy, published in April 2026 and stated to be uniform across depositories) offers issuer and ISIN lists in its shareable basket. It puts issuers' "contract" information in the non-shareable basket. It lists nothing from the Security and Covenant Monitoring System, where trust deeds and covenants are held. NSDL's guidelines require:

- a request form signed by the institution;
- an undertaking or NDA;
- that "On Completion of Duration of project, Data Seeker needs to purge the data".

### SEBI's own data

SEBI's guidelines for seeking its data share only "historical, anonymized" data at least two years old, under an undertaking of confidentiality. The source must be acknowledged in published work, and data must be expunged when the project ends. Anonymised data could not support an instrument-level record.

## What formal access could change

| Dimension | Likely effect | Why |
|---|---|---|
| Visibility | **Large.** Could show which debt filings exist for issuers whose own pages do not link them | Corporate announcements are in the first basket. Whether bulk data covers debt-only issuers and their attachments is not stated |
| Contract trace | **Possible.** Offer documents are listed | Whether private placement key information documents and trust deeds are included is not stated |
| Timing | **Large, if timestamps are included.** Dissemination times would replace Last-Modified estimates | The lists do not say whether announcement timestamps are provided |
| History | **Some.** Archives extend back years | Voluminous data has a six-month vintage, and the depth of debt filings is unknown |
| Reproducibility for others | **Worse, unless the terms allow publication.** Only eligible researchers could obtain the same data, under their own NDA | No route gives the public what the dataset would rest on |
| Openness of the published records | **At risk.** An NDA may forbid publishing instrument-level facts drawn from the data, and per-issuer records could be read as "investigative" | The policy is silent on publication and excludes investigative use |

## Assessment

Formal access is worth pursuing for what the open record cannot do:

- measure what open channels miss, for example the share of an issuer's mandated debt filings that its own site or its trustee's site also carries;
- date disclosures by the exchange's own dissemination record.

On the published terms it is not a way to build the public dataset. Facts that only NDA data could supply would have to stay out of the published records unless the agreement expressly permits publishing them at ISIN level with a citation. If access is obtained, keep it as a separate, restricted tier: never mixed into `data/`, labelled by licence, and published only as aggregates the agreement allows.

Open routes come first:

1. **Bond Central.** SEBI describes it as an "information repository for the public at large" with "corporate bond documents, and disclosures" (`bond-central-scope`, `bond-central-documents`). It was unreachable from the project's network on 3 and 4 November 2026. On 4 November 2026 it was also unreachable from the environment used for this assessment, though that environment's network policy blocked SEBI's and NSDL's hosts too, so this says nothing about the site. A person should open it in a browser on another network, read its terms, and record what it offers per ISIN. If it holds offer documents and disclosures under terms that allow citation, it could close more of the gap than any agreement.
2. **Manual retrieval of the BSE candidates**, under the existing manual-only policy ([coverage.md](coverage.md)).
3. **Issuers' own regulation 62 pages, searched systematically**, since regulation 62(1)(g) requires them to carry the compliance reports the issuer files.

## Questions to settle before any application

These are for the project owner to put, through the academic institution, if and when they choose to. Nothing has been sent.

1. May the derived facts be published under CC BY 4.0, at ISIN level? That means dates, levels, parties and the existence of a filing, with short quotations and a citation by exchange, filing date and time, and subject.
2. Does "Corporate Announcements" bulk data cover entities that list only debt, with their PDF attachments? Does it include dissemination timestamps?
3. Are debt offer documents, including key information documents of private placements, and trust deeds filed with the exchange included?
4. Does the six-month vintage apply to corporate data, and how far back do debt filings go?
5. Must data be purged when the project ends? May hashes, and records derived from the data, be kept?
6. Does a continuing public dataset on disclosure practice count as research rather than "investigative" use?
7. For NSE: may individual filings be linked or cited in a public dataset, under its hyperlinking policy?
8. For BSE: may a declared program retrieve individually cited documents, such as offer documents and trust deeds, at a polite rate? BSE refused the project's identified client on 4 November 2026.

## Sources read

| Document | Where it was read | Checked |
|---|---|---|
| SEBI circular SEBI/HO/DEPA-II/DEPA-II_SRG/P/CIR/2024/178, 20 December 2024 | [SEBI's PDF](https://www.sebi.gov.in/sebi_data/attachdocs/dec-2024/1734693561713.pdf) | 2026-11-04 |
| SEBI circular SEBI/HO/DEPA-III/DEPA-III_SSU/P/CIR/2022/25, 25 February 2022 | [SEBI's page](https://www.sebi.gov.in/legal/circulars/feb-2022/approach-to-securities-market-data-access-and-terms-of-usage-of-data-provided-by-data-sources-in-indian-securities-market_56420.html), text from reproductions | 2026-11-04 |
| Uniform Data Sharing Policy by Exchanges for Research Purposes and Analysis, v1.0, 27 June 2025 | [NCDEX's copy](https://www.ncdex.com/downloads/Others%202026/Data%20Feed%20policy/Annexure%202_Exchange%20Data%20Sharing%20Poilcy%20for%20Reseach.pdf) | 2026-11-04 |
| Data list under NSE Data Sharing Policy for Research and Analysis, 28 July 2025; NSE's "Data for Research" page; Data Seeking Request Form, 19 March 2025 | NSE's website (not linked, under NSE's hyperlinking policy) | 2026-11-04 |
| BSE market data products page; BSE Information Products Tariff, February 2025 | [BSE's page](https://www.bseindia.com/market_data_products.html?flag=eod) | 2026-11-04 |
| Data List for Depositories; NSDL Guidelines to Seek Data | [NSDL's list](https://nsdl.com/nsdl/2026-04/Policy%20for%20Sharing%20Data%20for%20the%20Purpose%20of%20Research%20%20Analysis%20Data%20List%20for%20Depositories.pdf), [NSDL's guidelines](https://nsdl.com/nsdl/2026-04/Guidelines%20to%20Seek%20Data.pdf) | 2026-11-04 |
| SEBI Guidelines for Seeking Data | [SEBI's PDF](https://www.sebi.gov.in/pdf/guidelines-of-data-sharing-final.pdf) | 2026-11-04, from a search excerpt only |

These were read through a third-party reading service, because this project's network could not reach the hosts. None of them is registered as a document in `data/`, because none is evidence for a record. The checked dates are for this assessment only.
