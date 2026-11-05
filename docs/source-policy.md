# Source policy

A public PDF is not automatically free to redistribute, and a website that can be reached is not automatically free to harvest. This page records what the project does for each kind of material and why. It is a research project's reasoning, not legal advice, and it has not been reviewed by a lawyer.

## Decisions by kind of material

| Material | Decision |
|---|---|
| **Source documents** | Never committed or redistributed. The repository holds the URL, SHA-256, size and dates, so anyone can obtain the same file and confirm it is the same file |
| **Extracted facts** (ISINs, dates, levels, parties, categories) | Published under CC BY 4.0. Facts are not owned, and the structure and annotations are the project's own work |
| **Quotations** | Short, attributed and only where needed to identify a passage. Not covered by the project's licence; see the limits below |
| **Contract clauses** | Quoted one clause at a time (up to 800 characters) for the instruments studied, because the wording is the subject of the research |
| **Annotations** (categories, parsed limits, plain-English notes) | The project's own work, under CC BY 4.0, and marked as annotations rather than source text |
| **Links** | Published, except for sources that require permission to link |
| **Code** | MIT |

## Quotation limits

Several trustees' sites restrict reuse of their content for public purposes without permission (see `data/sources.yaml`). The reports are regulatory disclosures made for the general public, and the project relies on fair dealing for research and review. It has not sought permission. To keep to that:

- quotations from trustee sites and from sites with similar terms are capped at **160 characters** per passage, and `brdo validate` fails on anything longer;
- numbers in a longer cell are kept as facts (`levels_stated`), so analysis does not need the wording;
- a cut cell is marked (`truncated`, `truncated_fields`), and the page reference lets a reader see the rest.

**What this leaves in the repository.** Measured on this release, quoted text amounts to these shares of each file's extracted text:

| Files | Share of text quoted | What the quoted text mainly is |
|---|---|---|
| Catalyst's quarterly report | About 36% | Names, ISINs, dates, the opening words of covenant cells |
| IDBI's and Axis's short quarterly reports | About 60% | Short cells: names, ISINs, dates, brief descriptions, and for Axis a list of issuer names |
| MITCON's report | About 33% | Names, dates, the opening words of cells |
| Vistra's report | Not meaningful, as much of the page has no text layer | As above |
| Trustee notices | 3% to 20% | The deed sentence, the opening words of a clause, whole clauses for pilot instruments |
| Issuers' covenant statements and auditors' certificates | Under 10% | Covenant names, required and actual levels and deed dates, which are facts, and one sentence of each conclusion |
| Dvara's regulation 59 intimation | Not meaningful, as the exchange's letter has no text layer | The existing and proposed wording of one covenant, quoted as contract clauses |
| Aye Finance's filing | About 31% | The existing and revised text of one covenant, which is the point of citing it |
| SEBI and ICRA documents | Under 5% | Single passages |

The 160-character cap is a restraint the project imposes on itself. It is not a legal threshold or a safe harbour, and fair dealing does not turn on a number of characters. This policy has not been reviewed by a lawyer. The questions a review should answer, and the facts it needs, are in [legal-review-brief.md](legal-review-brief.md). Until then, no limit is relaxed. That includes any reading of SEBI's circular of 25 February 2022 on free use of mandated disclosures.

These are high shares for the shortest reports, because a table of names and dates has little else in it. That is a judgement call, made on the basis that those items are facts. **If a rightsholder objects, the remedy is simple**: open an issue and the quotations from that source will be removed or reduced, leaving the facts and the link.

### Tables that are almost entirely facts

A trustee's census of monitored issues is a long table of company names, ISINs and dates. Its content is factual, but republishing it whole would reproduce the trustee's publication. The project therefore keeps only what it measures from the table, a small sample and the rows it relies on, and publishes the code that recomputes everything from the hashed file.

## Access rules by source

| Source | Pipeline retrieval | Why |
|---|---|---|
| SEBI | Allowed | robots.txt restricts only script and style paths. Republication requires permission, so circulars are linked and quoted briefly |
| Debenture trustees | Allowed | Nothing found addresses automated access. The fetcher honours robots.txt and crawl delays |
| Issuer websites cited | Allowed | Regulatory filings published for investors under regulation 62 of the LODR Regulations. Several issuers' terms restrict reproduction, so their quotations are capped at 160 characters like the trustees' |
| **Pahal Financial Services** | **Manual only** | Its home page answered the project's identified client on 4 November 2026, but its filings answered HTTP 403. Treated as an access restriction, like BSE |
| ICRA | Allowed | The rationale says contents may be used freely with acknowledgement |
| **BSE** | **Manual only** | Both hosts refused the project's identified client on 4 November 2026 while serving browsers. The project treats that as an access restriction and does not disguise its client |
| **CDSL and NSDL** | **Manual only** | CDSL's policy forbids downloading or storing its content without permission and allows links. A single value may be cited with its URL |
| **Online bond platforms** | **Manual only** | IndiaBonds' terms forbid data gathering tools, even though its robots.txt allows crawling |
| **NSE** | **Excluded** | As read on 3 November 2026, terms prohibit automated collection and storage, and hyperlinks without prior written permission. A re-reading on 5 November 2026 could not confirm the linking clause ([exchange-access.md](exchange-access.md#nses-website-terms)), so the exclusion stands until a person reads the pages. The dataset holds no NSE URL or content outside the source record, and tests enforce that |
| **Bond Central** | **Not assessed** | Unreachable when reviewed |

Formal research access to exchange data, under SEBI's circular of 20 December 2024, is assessed in [exchange-access.md](exchange-access.md). No application has been made. Any data obtained under an agreement would form a separate, restricted tier, never mixed into these records.

These rules are enforced in code: `Fetcher` refuses unregistered hosts and closed sources before making any request and re-checks after a redirect, `check_integrity` refuses records that break the policy, and `tests/test_dataset.py` checks the published data.

### What the fetcher will not do

It will not change its user agent, retry around a block, solve a challenge, use a login, or call an undocumented data API. It identifies itself as `bondholder-rights-observatory` with a link to this repository, keeps at least five seconds between requests to a host, and honours any longer crawl delay. Only two answers settle a host's robots policy: a robots file, which it obeys, or HTTP 404 or 410, which say there is none. Any other answer leaves the policy unknown, whether it is a refusal such as 403 or 429, a server error, a failed connection, or an HTML page where the robots file should be, as ICRA's bot-mitigation page is. It then fetches nothing from that host. It reports that as a failure to read the file, to be logged as an access error, not as a restriction the site never stated. An earlier version of the fetcher treated such answers as no robots file. ICRA's rationale `icra-krcl-139196` was retrieved under that rule on 4 November 2026, while ICRA's robots address returned a bot-mitigation page, and its record says so (`robots_at_retrieval: unread`). The file's hash and quotations are unaffected; what is uncertain is whether that retrieval followed the host's policy. The current fetcher refuses to fetch it again. The robots outcome of the other retrievals was not recorded at the time, so `documents.csv` leaves it empty rather than infer it.

### Manual retrieval

For a manual-only source, a person downloads the file in a browser and runs:

```console
$ brdo add-document "<url>" --id <id> --type key_information_document --title "<title>" --from-file <path>
```

This hashes the file into the local cache and marks the record `retrieved_manually`. Anyone else can do the same and `brdo verify` will confirm they hold an identical file. The candidates found so far are listed in the [observability report](observability-report.md#manual-checks).

## Reservations of AI-training rights

Beacon Trusteeship and Orbis publish `Content-Signal: search=yes,ai-train=no,use=reference` in their robots.txt. The project records this per source, and every row derived from such a source carries `ai_training_reserved = true`. Any future training or benchmark export must exclude those rows.

## Personal data

The dataset does not record natural persons. Notices can name signatories, compliance officers and even particular holders, and none of that is transcribed. Some issuers' quarterly compliance reports, published on their own sites, print lists of individual debenture holders with their addresses. Those pages are never transcribed or quoted, and the dataset cites only the pages that carry the covenant statement. A trustee's published list of companies is transcribed because the entities are companies. Dial-in details and meeting links printed in notices are not recorded.

## Statements about companies

Records are worded as attributed statements. The dataset says that a trustee reported a breach, and does not say that a company breached. Discrepancies are described neutrally and carry no inference about conduct. Corrections are welcome and will be recorded rather than silently applied.
