"""Re-checking every evidence anchor against the document it cites.

For each cited document the verifier obtains the exact file (from the cache,
or from the source if retrieval is permitted), confirms its SHA-256 matches the
recorded value, and then confirms that each quoted passage occurs on the cited
page. Matching is tried in increasingly tolerant ways and the method that
succeeded is reported, so a reader can tell an exact match from a match that
had to tolerate table layout.
"""

import html
import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from brdo.fetch import Cache, Fetcher, RetrievalFailed, RetrievalRefused, file_sha256
from brdo.models import Document, Evidence
from brdo.pdftext import audit_text_layer, normalize, page_texts
from brdo.store import Dataset

MAX_TOKEN_GAP = 12
"""Largest number of foreign tokens tolerated between consecutive quoted tokens.

Text extracted from multi-column tables interleaves neighbouring cells; a small
gap tolerance absorbs that without letting scattered words count as a match.
"""


_ISIN_PATTERN = re.compile(r"\bIN[A-Z0-9]{9}[0-9]\b")


class MatchMethod(StrEnum):
    NORMALIZED = "normalized"
    SPACELESS = "spaceless"
    TOKEN_SEQUENCE = "token_sequence"


class AnchorStatus(StrEnum):
    VERIFIED = "verified"
    VISUAL_ONLY = "visual_only"
    """Not in the text layer, and recorded as read from the rendered page; checking it means looking at the page."""
    WRONG_PAGE = "wrong_page"
    NOT_FOUND = "not_found"
    PAGE_OUT_OF_RANGE = "page_out_of_range"
    DOCUMENT_UNAVAILABLE = "document_unavailable"
    HASH_MISMATCH = "hash_mismatch"
    UNSUPPORTED_MEDIA = "unsupported_media"
    NO_QUOTE = "no_quote"


@dataclass(frozen=True)
class AnchorResult:
    label: str
    document: str
    page: int | None
    status: AnchorStatus
    method: MatchMethod | None = None
    found_on: tuple[int, ...] = ()
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status in (AnchorStatus.VERIFIED, AnchorStatus.VISUAL_ONLY, AnchorStatus.NO_QUOTE)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?|[%:<>=()]", normalize(text))


def _token_sequence_match(needle: list[str], haystack: list[str], max_gap: int = MAX_TOKEN_GAP) -> bool:
    if not needle:
        return False
    for start, token in enumerate(haystack):
        if token != needle[0]:
            continue
        position, matched = start, 1
        while matched < len(needle):
            window = haystack[position + 1 : position + 2 + max_gap]
            try:
                position = position + 1 + window.index(needle[matched])
            except ValueError:
                break
            matched += 1
        if matched == len(needle):
            return True
    return False


def match_on_page(page_text: str, quote: str) -> MatchMethod | None:
    target, page = normalize(quote), normalize(page_text)
    if target in page:
        return MatchMethod.NORMALIZED
    if target.replace(" ", "") in page.replace(" ", ""):
        return MatchMethod.SPACELESS
    if _token_sequence_match(_tokens(quote), _tokens(page_text)):
        return MatchMethod.TOKEN_SEQUENCE
    return None


def check_anchor(label: str, evidence: Evidence, pages: list[str]) -> AnchorResult:
    base = {"label": label, "document": evidence.document, "page": evidence.page}
    if not evidence.quote:
        return AnchorResult(status=AnchorStatus.NO_QUOTE, **base)
    if evidence.page is not None:
        if evidence.page > len(pages):
            return AnchorResult(
                status=AnchorStatus.PAGE_OUT_OF_RANGE, detail=f"document has {len(pages)} pages", **base
            )
        method = match_on_page(pages[evidence.page - 1], evidence.quote)
        if method is not None:
            return AnchorResult(status=AnchorStatus.VERIFIED, method=method, found_on=(evidence.page,), **base)
    found = [number for number, text in enumerate(pages, start=1) if match_on_page(text, evidence.quote)]
    if found and evidence.page is None:
        method = match_on_page(pages[found[0] - 1], evidence.quote)
        return AnchorResult(status=AnchorStatus.VERIFIED, method=method, found_on=tuple(found), **base)
    if found:
        return AnchorResult(status=AnchorStatus.WRONG_PAGE, found_on=tuple(found), **base)
    if evidence.visual_fallback:
        return AnchorResult(status=AnchorStatus.VISUAL_ONLY, **base)
    return AnchorResult(status=AnchorStatus.NOT_FOUND, **base)


def html_text(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    return [html.unescape(re.sub(r"<[^>]+>", " ", raw))]


@dataclass
class DocumentText:
    pages: list[str] | None
    problem: AnchorStatus | None = None
    detail: str = ""


def load_document_text(document: Document, cache: Cache, fetcher: Fetcher | None) -> DocumentText:
    if document.sha256 is None:
        return DocumentText(None, AnchorStatus.DOCUMENT_UNAVAILABLE, "document was never retrieved")
    path = cache.get(document.sha256)
    if path is None and fetcher is not None:
        try:
            retrieved = fetcher.fetch(document.url)
        except (RetrievalRefused, RetrievalFailed) as error:
            return DocumentText(None, AnchorStatus.DOCUMENT_UNAVAILABLE, str(error))
        if retrieved.sha256 != document.sha256:
            return DocumentText(
                None,
                AnchorStatus.HASH_MISMATCH,
                f"source now serves {retrieved.sha256}; recorded {document.sha256}",
            )
        path = retrieved.path
    if path is None:
        return DocumentText(None, AnchorStatus.DOCUMENT_UNAVAILABLE, "not in local cache (run without --offline)")
    if file_sha256(path) != document.sha256:
        return DocumentText(None, AnchorStatus.HASH_MISMATCH, f"cached file {path} is corrupt")
    if document.media_type == "application/pdf":
        return DocumentText(page_texts(path, document.sha256, cache.root))
    if document.media_type in ("text/html", "application/xhtml+xml"):
        return DocumentText(html_text(path))
    return DocumentText(None, AnchorStatus.UNSUPPORTED_MEDIA, f"no text extractor for {document.media_type}")


def verify_dataset(dataset: Dataset, cache: Cache, fetcher: Fetcher | None) -> list[AnchorResult]:
    anchors: dict[str, list[tuple[str, Evidence]]] = {}
    for label, evidence in dataset.evidence():
        anchors.setdefault(evidence.document, []).append((label, evidence))
    results: list[AnchorResult] = []
    for document_id in sorted(anchors):
        document = dataset.documents.get(document_id)
        if document is None:
            continue
        text = load_document_text(document, cache, fetcher)
        for label, evidence in anchors[document_id]:
            if text.pages is None:
                results.append(
                    AnchorResult(
                        label=label,
                        document=document_id,
                        page=evidence.page,
                        status=text.problem or AnchorStatus.DOCUMENT_UNAVAILABLE,
                        detail=text.detail,
                    )
                )
            else:
                results.append(check_anchor(label, evidence, text.pages))
    return results


def untranscribed_isins(dataset: Dataset, cache: Cache, fetcher: Fetcher | None) -> list[tuple[str, str]]:
    """ISINs printed in a report's text layer but missing from its supposedly complete transcription."""
    missing: list[tuple[str, str]] = []
    for report in dataset.breach_reports.values():
        if not report.extraction_complete:
            continue
        text = load_document_text(dataset.documents[report.document], cache, fetcher)
        if text.pages is None:
            continue
        printed = set(_ISIN_PATTERN.findall(" ".join(text.pages)))
        transcribed = {isin for row in report.rows for isin in row.isins}
        missing.extend((report.document, isin) for isin in sorted(printed - transcribed))
    return missing


def text_layer_warnings(dataset: Dataset, cache: Cache) -> list[tuple[str, int, str]]:
    """Pages of cached PDFs whose text layer probably omits what a reader can see."""
    warnings: list[tuple[str, int, str]] = []
    for document_id in sorted(dataset.documents):
        document = dataset.documents[document_id]
        path = cache.get(document.sha256) if document.sha256 else None
        if path is None or document.media_type != "application/pdf":
            continue
        for page in audit_text_layer(path):
            if page.problem:
                warnings.append((document_id, page.page, page.problem))
    return warnings


def summarize(results: Iterable[AnchorResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        key = result.status.value if result.method is None else f"{result.status.value}:{result.method.value}"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
