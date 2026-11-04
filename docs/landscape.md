# What already exists

Reviewed on 3 and 4 November 2026. Where a statement rests on a regulatory text, the checked passage is in [`data/regulatory-references.yaml`](../data/regulatory-references.yaml).

## The regulatory framework

The governing text is SEBI's **Master Circular for Debenture Trustees** of 28 September 2026 ([PDF](https://www.sebi.gov.in/sebi_data/attachdocs/sep-2026/1790593347737.pdf)). The parts that shape this project are:

| Chapter | What it requires | Consequence here |
|---|---|---|
| III | A Security and Covenant Monitoring System hosted by depositories, with login credentials for issuers, rating agencies and trustees. Issuers enter covenants and upload the trust deed within five working days of signing | The fullest record exists but is credentialed |
| VI | Quarterly compliance status on financial covenants; trustees monitor breaches and publish a status report on their website and to the exchange. Annex-VIA is a guidance note listing covenant categories | The basis of the reports used here, and of the covenant taxonomy |
| VII | Website disclosures in prescribed tables. Table 5 covers covenant breaches: ISIN, covenant, date of breach, date of detection, intimation, delays, action taken | The main event source |
| IX | An investor charter: copies of the trust deed to investors, inspection rights | A route to deeds, framed for investors |
| X | Default is reckoned at ISIN level. One ISIN may span several offer documents. Notice within three days and a meeting within 30 days of a breach or default | The reason for the ISIN key and many-to-many links; and the source of the notices used here |

The **circular of 27 October 2026** ([PDF](https://www.sebi.gov.in/sebi_data/attachdocs/oct-2026/1793167964839.pdf)) extends to 27 April 2027 the deadline for trustees to move non-SEBI activities into separate business units. It does not change covenant monitoring. It does record that in June 2026 SEBI set up an expert working group to review the trustee framework, so the rules may change, which is one reason every report keeps its own regulatory reference.

## Existing systems

| System | What it offers, as observed | Overlap with this project |
|---|---|---|
| **Security and Covenant Monitoring System** (depositories) | Covenants, deeds, security and monitoring data, for registered stakeholders. NSDL's page describes no public view | Holds the authoritative data but is not public. This project does not try to replicate it |
| **Bond Central** (OBPP Association with exchanges and depositories, launched 27 February 2025) | Described by SEBI as a free public repository with listings, price comparison, risk assessments, documents and disclosures | Could not be assessed: connections were refused from this project's network and from an independent fetching service on 3 November 2026, and again on 4 November. **Its actual depth needs checking** before any claim about what it lacks |
| **CDSL Corporate Bond Database** and NSDL India Bond Info | Per-ISIN identity, terms, ratings and payment fields. CDSL's terms forbid storing the content but allow links | Reference data. The trustee field disagreed with the reporting trustee for both ISINs examined |
| **BSE** | Hosts key information documents, placement memoranda and trust deeds at public URLs; refuses identified automated clients | The main contract channel, reachable only in a browser |
| **NSE** | Hosts filings. Terms prohibit automated collection and hyperlinks without permission | Excluded from this release |
| **Online bond platforms** such as IndiaBonds | Per-ISIN pages, some linking issue documents. Terms prohibit extraction tools | A place to look by hand |
| **Debenture trustees' websites** | Table 5 reports, notices, press releases | The main source for this release |
| **Rating agencies** | Rationales, some stating "salient covenants" and reporting breaches | A useful independent cross-check |

## Adjacent work

- [Flock](https://useflock.in/blog/what-must-a-debenture-trustee-disclose-on-its-website) publishes a filings digest with sources and dates, and explains trustee disclosure rules. Its public pages describe no ISIN-level covenant dataset.
- [stock-market-circulars](https://rhnvrm.github.io/stock-market-circulars/) is an open mirror of exchange circulars, which helped show that notices about debt securities exist. This project does not rely on it as evidence.
- Commercial data vendors and bond platforms cover instrument terms and prices, not the evidence chain from clause to breach, as far as their public pages show.
- In academic work, covenant research is mostly outside India: for example [this study of US bond covenants from 1980 to 2014](https://www.sciencedirect.com/science/article/abs/pii/S0929119920302431), and the [OECD's paper on bonds and bondholder rights](https://www.oecd.org/content/dam/oecd/en/publications/reports/2015/02/corporate-bonds-bondholders-and-corporate-governance_g17a25c5/5js69lj4hvnw-en.pdf). The searches logged for this project found no empirical study of covenants in Indian trust deeds, which is a weak negative: Indian legal and finance journals are not well covered by the tool used.

## What this project does and does not add

**It does not add:**

- a bond directory, price feed or listing portal;
- covenant monitoring, which SEBI's system and the trustees perform;
- a judgement about any issuer's compliance or any bond's safety.

**It may add, subject to the checks above:**

- a machine-readable record of trustees' Table 5 reports across trustees, with each field tied to a page. No public aggregation surfaced in the searches run, which does not establish that none exists;
- the link between ISIN, trust deed dates, clause and reported event;
- version history of disclosures that otherwise disappear when replaced;
- an explicit, status-based account of what is not known;
- a measured account of where public availability stops short of research access.
