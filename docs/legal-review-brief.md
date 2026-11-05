# Brief for legal review

Prepared on 4 November 2026 for an Indian lawyer advising on copyright, database, contract and data protection questions. It sets out what the project does and asks questions. It draws no legal conclusions: none of the project's policies has yet been reviewed by a lawyer, and the project does not treat any of its own limits as a safe harbour.

## What the project is

An open, source-linked dataset of the contractual protections attached to individual Indian listed non-convertible debentures, and of the public disclosures about them: debenture trustees' breach reports and letters to holders, issuers' and auditors' covenant statements, exchange approvals and rating rationales. It is published in a public GitHub repository for research, by researchers who may approach the exchanges through an academic institution. It is non-commercial.

## What it stores and publishes

| Material | Treatment |
|---|---|
| Source documents (PDFs, pages) | **Never published.** Each is identified by URL, SHA-256, size and dates. Copies are kept only in a private local cache, to verify quotations |
| Extracted facts | Published under CC BY 4.0: ISINs, dates, levels, parties, and which document says what |
| Short quotations | Published to identify each passage relied on, and excluded from the licence. For sources whose terms restrict reuse, at most 160 characters per passage, a limit the project set itself |
| Contract clauses | Quoted one clause at a time, up to 800 characters, because the wording is what is studied |
| Annotations and derived measures | The project's own work, under CC BY 4.0 |
| A trustee's census table (1,832 ISINs) | Not republished. Only counts, a reproducible sample of 20 ISINs, a list of 59 ISINs whose compliance report is marked not received, and 17 cited rows |
| Single values seen on depository pages | Recorded with the page's URL and the date seen; the page is not stored |
| Personal data | Not recorded. Tests reject e-mail addresses, PANs, depository participant IDs and written-out phone numbers in the published files |

**How much of a document the quotations amount to.** For the shortest trustee reports, which are tables of names, ISINs, dates and brief descriptions, quoted text is about 60% of the file's extracted text. For Catalyst's longer report it is about 36%, and for most letters and filings between 3% and 31% (see [source-policy.md](source-policy.md)).

## The sources' terms, as summarised by the project

The project's summaries are in `data/sources.yaml`, with the date each was read.

- **Debenture trustees.** Several sites' notices say their content may not be distributed, reused or used "for public or commercial purposes" without written permission. The breach reports themselves say they are published "for information of Debenture Holders, Other Intermediaries and General Public".
- **Issuers.** Several sites' terms forbid reproduction or republication without permission. They publish their compliance filings under regulation 62 of SEBI's Listing Obligations and Disclosure Requirements Regulations.
- **BSE.** A disclaimer prohibits reproduction or redistribution. Its servers refused the project's identified client while serving browsers.
- **NSE.** As recorded on 3 November 2026, its terms prohibit systematic or automated data collection and storing or republishing content without permission, and its hyperlinking policy requires prior written permission for links. A re-reading on 5 November 2026 could not confirm either clause: the hyperlinking policy as returned says nothing about others linking to NSE, and the quoted prohibition matches the terms of an NSE Data platform word for word ([exchange-access.md](exchange-access.md#nses-website-terms)). The project neither retrieves from NSE nor links to it until a person reads the pages in a browser.
- **CDSL.** No copying, downloading or storage without permission; links are allowed.
- **A bond platform** forbids data-gathering and extraction tools and derivative databases.
- **ICRA's rationale** says its contents may be used freely with acknowledgement.
- **Two trustees' robots.txt files** publish `Content-Signal: search=yes,ai-train=no,use=reference`.

## Regulatory context that may bear on the questions

- SEBI's circular of 25 February 2022 (SEBI/HO/DEPA-III/DEPA-III_SSU/P/CIR/2022/25). It is addressed among others to exchanges, depositories, rating agencies and debenture trustees, and says that data provided "pursuant to regulatory mandates for reporting and disclosure in public domain" should be available "free of charge" for viewing, for download "as well as their usage for the value addition purposes". SEBI's master circulars have since rescinded it for some intermediaries, whose master circulars carry its wording, but no rescission for exchanges, depositories or debenture trustees was found. See [exchange-access.md](exchange-access.md).
- SEBI's circular of 20 December 2024 (SEBI/HO/DEPA-II/DEPA-II_SRG/P/CIR/2024/178) on sharing data for research by accredited academic institutions. The exchanges' uniform policy under it may require a binding NDA and excludes "investigative purposes".
- Regulation 62(1)(g) of the LODR Regulations requires issuers' websites to carry "all information and reports including compliance reports filed by the listed entity".
- SEBI's master circular for debenture trustees requires the breach status report to be furnished "on its website and to the Stock Exchange".

## Questions

**Copyright and fair dealing**

1. Does fair dealing for research, or for criticism or review, under section 52(1)(a) of the Copyright Act, 1957, cover a public dataset that quotes up to 160 characters per passage, when the quotations amount to as much as 60% of a short tabular report's text? Does it matter that the dataset is a research resource rather than a critique, and that its purpose is to audit the disclosures quoted?
2. Are trustees' breach reports and letters, and issuers' covenant statements, which are prescribed regulatory formats, protected works? Is a trustee's table of names, ISINs and dates protected as a compilation? Does publishing facts extracted from them raise any issue?
3. May contract clauses be quoted at up to 800 characters, from trustees' letters, issuers' filings, offer documents and, in future, executed trust deeds obtained manually? Does it matter that the clause is the subject of the analysis?

**Website terms and access**

4. What is the effect, if any, of terms that restrict public or commercial reuse on reading, on downloading by a declared and polite program, on quoting, and on publishing extracted facts? Does SEBI's 2022 circular bear on terms applied to mandated disclosures?
5. Is a file downloaded manually in a browser, from a site that refuses programs, any different in status for these purposes?
6. May a document hosted on a bond platform whose terms forbid derivative databases be used, when the document is an issuer's offer document?

**Links and citation**

7. What do NSE's terms and hyperlinking policy actually require of a site that cites or links its filings? Is citing a filing by its title, date and identifier, without a link, consistent with them? Are deep links to PDFs on other sites a concern?

**Storage, archives and the data licence**

8. May the project keep private copies of source files for verification, and share them with collaborators who are verifying the dataset?
9. May it ask a public web archive to capture a source file, to preserve evidence and its date?
10. Is CC BY 4.0, with quotations carved out, an adequate licence for a dataset that contains third-party quotations? Is the carve-out drafted adequately in `LICENSE-DATA.md`?

**Statements about companies**

11. Records say that a named trustee or issuer stated something, for example that a breach was reported, and never that a company breached. Is that attribution, with a corrections and takedown policy, adequate protection against claims by issuers or trustees?

**Personal data**

12. Does the Digital Personal Data Protection Act, 2023 apply to incidental personal data in public regulatory documents the project reads but does not record? Should the project record the names of signatories or officers if a future analysis needs them?

**AI reservations and automated processing**

13. Some sources publish an `ai-train=no` signal. Does automated or AI-assisted processing of their documents for transcription engage that reservation? What must downstream users be told?

**Formal research access**

14. If an exchange's research NDA forbids publishing derived data, how should a restricted tier be kept separate from the public dataset? Could aggregate findings from it be published?

## Where the project would act on advice

- The 160-character cap and the 800-character clause limit.
- The decision to cite but not store depository values.
- The manual-only treatment of BSE and platforms, and the exclusion of NSE.
- Whether the census sample and its not-received list may be published.
- The terms on which, if ever, exchange research data could be used.
