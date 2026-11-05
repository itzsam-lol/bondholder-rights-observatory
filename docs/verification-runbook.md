# Verification runbook

How to re-check the dataset's evidence against its sources, from a machine whose network can reach them. Written on 5 November 2026. The cloud environment used to build the last three passes could not reach any source host, so this has not been done since 4 November 2026.

## What is carried forward, and what a run would replace

The last full run of `brdo verify`, on 4 November 2026, checked all 1,254 anchors:

- 1,147 were found by machine in the file's text layer;
- 107 were `visual_only`: anchors recorded as transcribed from the rendered page whose words the text layer does not hold, so that checking them means looking at the page.

Separately, 246 anchors are recorded as transcribed from the rendered page (`read_from_rendering` in `exports/evidence.csv`). That is a fact about how they were transcribed, not a verification result. `brdo verify` reports an anchor as `visual_only` only if it is one of those 246 and its words are not in the text layer, so the 107 are among the 246; at that run the other 139 were found in the text layer.

Those figures stay as they are, dated 4 November 2026. A new run adds new, dated figures beside them and never overwrites them.

## Kinds of check

| Check | Command | Needs |
|---|---|---|
| Schema and integrity | `uv run brdo validate` | Nothing beyond the repository |
| Tests | `uv run pytest` | Nothing; two tests run only once the cache holds the files |
| Rebuilding the exports | `uv run brdo build --out <dir>`, compared with `exports/` | Nothing |
| The data package | `uvx --from 'frictionless==5.18.1' frictionless validate exports/datapackage.json` | The package index, to install the validator |
| Retrieving the files | `uv run brdo fetch` | The 13 hosts below |
| Anchors against the cached files | `uv run brdo verify --offline` | A cache filled by `brdo fetch` |
| Text layers | `uv run brdo audit-text` | The cache |
| The sources still serve the recorded files | `uv run pytest -m network` | The 13 hosts |
| The sources' terms and robots policies | A person reads them | A browser |
| Anchors read from the rendering | A person compares them with the rendered pages | The files, and a PDF viewer |
| The annotations | An independent person (see [reliability.md](reliability.md#review-protocol)) | The review packet |

No check stands in for another. In particular, tests and rebuilds show that the code and records agree with each other; only `brdo verify` against the files shows that the records agree with the sources.

## Before retrieving anything

1. **Use a machine and network you are permitted to use** for automated retrieval, with no proxy that rewrites TLS. Do not change the fetcher's user agent, and do not retry around a refusal.
2. **Re-read each source's terms.** `data/sources.yaml` records, for each source, the pages read and the date (3 or 4 November 2026). If a source's terms now forbid automated access, stop: change that source's `retrieval` to `manual_only`, with the maintainer's approval, before running `brdo fetch`.
3. **Establish the robots policy of the five hosts whose policy the source records do not document:** `dlryl1dmmgapd.cloudfront.net` (Aye Finance's document host), `www.dvarakgfs.com`, `satyamicrocapital.com`, `www.infinityfincorp.com` and `www.mitconcredentia.in`. Open each host's `/robots.txt` in a browser and record what it says in the source record. The fetcher reads robots.txt itself before every host, but the earlier version that retrieved these files treated a refusal or an HTML page as no robots file, so whether those retrievals followed the hosts' policies was never recorded.
4. **ICRA.** ICRA's rationale (`icra-krcl-139196`) was retrieved on 4 November 2026 while ICRA's robots address returned a bot-mitigation page, and its record says so (`robots_at_retrieval: unread`). Leave that record as it is. The fetcher will try ICRA's robots.txt again. If it still cannot read a robots file, it fetches nothing and reports an access error; the rationale's two anchors then stay unverified in this run. Do not work around that.
5. **Nothing from BSE, NSE, depositories or bond platforms is fetched.** None of the 45 documents comes from them, and the fetcher refuses them by policy.

## Running it

From the repository's root, on the commit you mean to verify:

```bash
git rev-parse HEAD
```

```bash
uv sync
```

Keep the cache outside the repository. Source files must never be committed; `.cache/` and `*.pdf` are ignored by git, but a separate folder is safer:

```bash
export BRDO_CACHE="$HOME/brdo-cache"
```

Then run the checks and keep every output. This writes a dated folder outside the repository:

```bash
RUN="$HOME/brdo-verification/$(date -u +%Y-%m-%d)-$(git rev-parse --short HEAD)"
mkdir -p "$RUN"
git rev-parse HEAD > "$RUN/commit.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/started.txt"
{ uv --version; uv run python --version; uname -a; } > "$RUN/environment.txt" 2>&1
uv run brdo validate > "$RUN/validate.log" 2>&1; echo "exit $?" >> "$RUN/validate.log"
uv run brdo fetch > "$RUN/fetch.log" 2>&1; echo "exit $?" >> "$RUN/fetch.log"
uv run brdo verify --offline > "$RUN/verify.log" 2>&1; echo "exit $?" >> "$RUN/verify.log"
uv run brdo audit-text > "$RUN/audit-text.log" 2>&1; echo "exit $?" >> "$RUN/audit-text.log"
uv run pytest -q -rs > "$RUN/pytest.log" 2>&1; echo "exit $?" >> "$RUN/pytest.log"
uv run pytest -m network -q -rs > "$RUN/pytest-network.log" 2>&1; echo "exit $?" >> "$RUN/pytest-network.log"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN/finished.txt"
```

`brdo fetch` and `brdo verify` are run separately on purpose. `brdo verify` without `--offline` would fetch missing files itself, which mixes retrieval with verification. The logs hold document ids, pages, record labels and statuses, but no quotations or source files, so the folder can be kept as the run's record. Commit it to the repository only with the maintainer's approval.

## Reading the results

- **`fetch.log`.** Each document not yet in the cache is `ok`, `CHANGED at source (now <sha256>)`, or a refusal or failure with its reason, such as robots.txt being unread. Any line that is not `ok` makes the exit status 1. The fetcher waits at least five seconds between requests to a host, and longer where a host's robots file asks, so a full run takes several minutes.
- **`verify.log`.** The last lines count anchors by status, such as `verified:exact` or `visual_only`. Lines above them list every anchor that did not verify, with its document, page and record. The run fails on any anchor that is neither verified nor `visual_only` (an anchor with no quotation is not checked), on an ISIN that a file prints but its transcription omits, and on a census whose count or sample does not reproduce.
- **`pytest.log`.** With the cache filled, the two tests that skip without it should run: every anchor against the cached files, and every census reproduced from its file.

What to do with each kind of result:

| Result | Meaning | Action |
|---|---|---|
| `verified` | The words are on the cited page of the hashed file | None |
| `visual_only` | The words are not in the text layer, and the record says they were read from the rendered page | A person checks them against the rendered page (below) |
| `wrong_page`, `not_found`, `page_out_of_range` | The record may misquote or mis-cite the file | A person looks at the page. Correct the record only with that evidence, and log the correction in `CHANGELOG.md` |
| `hash_mismatch`, or `CHANGED at source` | The publisher now serves a different file at that address | Leave the record and its hash as they are. Register the new file as a new document that supersedes the old one, under the source policy. The old record's anchors stay unverified until the original file is found again |
| `document_unavailable` | The file could not be retrieved | Record the failure, with its reason, as an access error; the anchors stay unverified in this run |

Record the run's figures as a new, dated entry in `CHANGELOG.md` and in [reliability.md](reliability.md), beside the 4 November 2026 figures, with the commit verified and the path of the run's logs.

## The hosts, and what each serves

| Host | Source | Documents | Anchors | Read from the rendering | Robots policy documented in the source record |
|---|---|---|---|---|---|
| `catalysttrustee.com` | `catalyst-trusteeship` | 15 | 593 | 0 | Yes |
| `idbitrustee.com` | `idbi-trusteeship` | 10 | 238 | 24 | Yes |
| `www.dvarakgfs.com` | `dvara-kgfs-web` | 3 | 155 | 154 | No |
| `www.axistrustee.in` | `axis-trustee` | 3 | 127 | 0 | Yes |
| `www.vistraitcl.com` | `vistra-itcl` | 1 | 56 | 40 | Yes |
| `satyamicrocapital.com` | `satya-microcapital-web` | 1 | 31 | 28 | No |
| `www.sebi.gov.in` | `sebi` | 6 | 28 | 0 | Yes |
| `mitconcredentia.in` | `mitcon-credentia` | 1 | 11 | 0 | Yes |
| `www.infinityfincorp.com` | `infinity-fincorp-web` | 1 | 6 | 0 | No |
| `dlryl1dmmgapd.cloudfront.net` | `aye-finance-web` | 1 | 5 | 0 | No |
| `www.icra.in` | `icra` | 1 | 2 | 0 | Unread at retrieval |
| `beacontrustee.co.in` | `beacon-trusteeship` | 1 | 1 | 0 | Yes |
| `www.mitconcredentia.in` | `mitcon-credentia` | 1 | 1 | 0 | No |

The documents on each host:

- **`catalysttrustee.com`:** `ctl-t5-2026-06`, `ctl-qcr-2026-06`, and the letters `ctl-notice-akara-2026-08`, `ctl-notice-aye-2026-10`, `ctl-notice-aye-ine501x07570-2026-05`, `ctl-notice-aye-ine501x07588-2026-09`, `ctl-notice-casablanca-2026-08`, `ctl-notice-convenient-2026-08`, `ctl-notice-dvara-2026-08`, `ctl-notice-infinity-2026-08`, `ctl-notice-light-2026-08`, `ctl-notice-neogrowth-2026-08`, `ctl-notice-pahal-2026-08`, `ctl-notice-samunnati-2026-08`, `ctl-notice-satya-2026-08`.
- **`idbitrustee.com`:** `idbi-t5-2026-06`, and the letters `idbi-notice-aliens-2026-09b`, `idbi-notice-belstar-2026-07`, `idbi-notice-dvara-2026-08`, `idbi-notice-emami-2026-09`, `idbi-notice-konkan-2026-05`, `idbi-notice-konkan-2026-09`, `idbi-notice-mecl-2026-08`, `idbi-notice-pidb-2026-08`, `idbi-notice-pvp-2026-06`.
- **`www.dvarakgfs.com`:** `dvara-reg54-2026-02-11`, `dvara-reg59-2026-07-02`, `dvara-sc-2026-08-12`.
- **`www.axistrustee.in`:** `axis-t5-2026-06-v20260814`, `axis-t5-2026-06-v20260916`, `axis-t5-2026-09-v20261029`.
- **`www.sebi.gov.in`:** `sebi-mc-dt-2026-09-28`, `sebi-lodr-2026-10-15`, `sebi-circ-dt-sbu-2026-10-27`, `sebi-mc-cra-2025-07-11`, `sebi-pr-bond-central-2025-02-27`, `sebi-pr-ewg-2026-06-30`.
- **One document each:** `vistra-t5-2026-06`, `satya-qcr-2026-06`, `mitcon-t5-2026-06`, `infinity-sc-2026-08-07`, `aye-walco-outcome-2025-09-02`, `icra-krcl-139196`, `beacon-t5-2026-06`, `mitcon-press-ramasigns-2026-08-14`.

Each document's address and SHA-256 are in `exports/documents.csv`, and its anchors in `exports/evidence.csv`.

## Documents a person must check by eye

These nine files hold the 246 anchors transcribed from the rendered page, because their text layer is missing, outlined or unreliable for those passages. A fresh `brdo verify` will say which of them are `visual_only`; each of those must be compared with the rendered page, and the result recorded:

| Document | Anchors read from the rendering |
|---|---|
| `dvara-sc-2026-08-12` | 86 |
| `dvara-reg54-2026-02-11` | 64 |
| `vistra-t5-2026-06` | 40 |
| `satya-qcr-2026-06` | 28 |
| `idbi-notice-mecl-2026-08` | 9 |
| `idbi-notice-pidb-2026-08` | 9 |
| `dvara-reg59-2026-07-02` | 4 |
| `idbi-notice-dvara-2026-08` | 3 |
| `idbi-notice-pvp-2026-06` | 3 |

`uv run brdo page <document> <page>` prints a page's text layer, and `uv run brdo find <document> "<text>"` lists the pages whose text layer holds some words, which helps to see what the text layer lacks.
