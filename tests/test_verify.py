"""Evidence checking: exact where possible, tolerant only in reported ways, and honest about what it could not check."""

from pathlib import Path

import pytest

from brdo.fetch import Cache, Fetcher, HttpResponse, file_sha256
from brdo.models import Evidence
from brdo.pdftext import audit_text_layer, extract_pages, normalize, page_texts
from brdo.verify import (
    AnchorStatus,
    MatchMethod,
    check_anchor,
    match_on_page,
    summarize,
    text_layer_warnings,
    untranscribed_isins,
    verify_dataset,
)
from tests.conftest import ISIN_LISTED, make_document, make_report, make_row, text_stream, write_pdf


def anchor(quote: str | None, page: int | None = 1, **options) -> Evidence:
    return Evidence(document="doc", page=page, quote=quote, **options)


@pytest.mark.parametrize(
    "printed, quoted",
    [
        ("maintain   a ratio\nof less than 5%", "maintain a ratio of less than 5%"),
        ("MAINTAIN A RATIO", "maintain a ratio"),
        ("the Company’s “Security Cover” – 1.10x", 'the Company\'s "Security Cover" - 1.10x'),
        ("the debt-equity raƟo", "the debt-equity ratio"),
        ("Porƞolio at Risk, SeƩlement Date", "Portfolio at Risk, Settlement Date"),
    ],
)
def test_normalisation_absorbs_what_extraction_introduces(printed, quoted):
    assert match_on_page(printed, quoted) is MatchMethod.NORMALIZED


def test_broken_words_fall_back_to_a_spaceless_match():
    assert (
        match_on_page("Intimation to Debenture Holders 24- 07-2026", "Debenture Holders 24-07-2026")
        is MatchMethod.SPACELESS
    )


def test_interleaved_table_columns_fall_back_to_a_bounded_token_match():
    page = "Name Breach of security cover Date 22-07-26 ratio as prescribed 22-07-26 NA in the deed"
    assert match_on_page(page, "security cover ratio as prescribed in the deed") is MatchMethod.TOKEN_SEQUENCE


def test_scattered_words_do_not_count_as_a_match():
    filler = " ".join(f"word{index}" for index in range(40))
    assert match_on_page(f"security {filler} cover", "security cover") is None


def test_a_different_threshold_is_not_a_match():
    assert match_on_page("maintain a ratio of less than 6%", "maintain a ratio of less than 5%") is None


def test_a_quote_on_the_cited_page_is_verified():
    result = check_anchor("x", anchor("hello there"), ["hello there"])
    assert result.status is AnchorStatus.VERIFIED and result.ok


def test_a_quote_on_another_page_is_flagged_with_where_it_was_found():
    result = check_anchor("x", anchor("hello there", page=1), ["nothing", "hello there"])
    assert result.status is AnchorStatus.WRONG_PAGE
    assert result.found_on == (2,)
    assert not result.ok


def test_a_quote_nowhere_fails():
    assert check_anchor("x", anchor("hello there"), ["nothing"]).status is AnchorStatus.NOT_FOUND


def test_a_page_beyond_the_file_fails():
    assert check_anchor("x", anchor("hello there", page=9), ["hello there"]).status is AnchorStatus.PAGE_OUT_OF_RANGE


def test_a_pageless_anchor_searches_the_whole_file():
    result = check_anchor("x", anchor("hello there", page=None), ["nothing", "hello there"])
    assert result.status is AnchorStatus.VERIFIED and result.found_on == (2,)


def test_words_read_from_the_rendering_are_reported_separately_from_machine_verified_ones():
    result = check_anchor("x", anchor("hello there", visual_fallback=True), ["nothing"])
    assert result.status is AnchorStatus.VISUAL_ONLY
    assert result.ok
    assert summarize([result]) == {"visual_only": 1}


def test_a_visual_fallback_still_prefers_the_text_layer():
    result = check_anchor("x", anchor("hello there", visual_fallback=True), ["hello there"])
    assert result.status is AnchorStatus.VERIFIED


def test_a_wrong_page_is_not_excused_by_a_visual_fallback():
    result = check_anchor("x", anchor("hello there", visual_fallback=True), ["nothing", "hello there"])
    assert result.status is AnchorStatus.WRONG_PAGE


def test_words_read_from_a_page_without_any_text_layer_are_not_contradicted_by_other_pages():
    result = check_anchor("x", anchor("hello there", page=1, visual_fallback=True), ["  ", "hello there"])
    assert result.status is AnchorStatus.VISUAL_ONLY
    assert "no text layer" in result.detail


def _dataset_with_pdf(
    dataset,
    tmp_path: Path,
    text: str = f"Covenant maintain a ratio of less than 5% {ISIN_LISTED} Example Finance Limited 30-06-26 14-08-26",
):
    pdf = write_pdf(tmp_path / "report.pdf", [text_stream(text)])
    cache = Cache(tmp_path / "cache")
    sha256, _ = cache.store(pdf.read_bytes(), {})
    dataset.documents["report-q1"] = make_document(sha256=sha256, pages=1)
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": []})
    dataset.instruments["INE501X07570"] = dataset.instruments["INE501X07570"].model_copy(update={"claims": []})
    return cache, sha256


def test_text_is_extracted_per_page_from_a_real_pdf(tmp_path):
    pdf = write_pdf(tmp_path / "two.pdf", [text_stream("first page"), text_stream("second page")])
    pages = extract_pages(pdf)
    assert [normalize(page) for page in pages] == ["first page", "second page"]


def test_extracted_pages_are_memoised_by_hash(tmp_path):
    pdf = write_pdf(tmp_path / "one.pdf", [text_stream("only page")])
    first = page_texts(pdf, "abc", tmp_path)
    pdf.unlink()
    assert page_texts(pdf, "abc", tmp_path) == first


def test_a_faithful_transcription_verifies_end_to_end(dataset, tmp_path):
    cache, _ = _dataset_with_pdf(dataset, tmp_path)
    results = verify_dataset(dataset, cache, None)
    assert results
    assert all(result.ok for result in results)
    assert {result.status for result in results} == {AnchorStatus.VERIFIED}


def test_a_transcription_error_is_caught_end_to_end(dataset, tmp_path):
    cache, _ = _dataset_with_pdf(dataset, tmp_path, text=f"Covenant maintain a ratio of less than 6% {ISIN_LISTED}")
    failures = [result for result in verify_dataset(dataset, cache, None) if not result.ok]
    assert any(result.status is AnchorStatus.NOT_FOUND for result in failures)


def test_a_document_missing_from_the_cache_is_unavailable_not_verified(dataset, tmp_path):
    results = verify_dataset(dataset, Cache(tmp_path / "empty"), None)
    assert results and all(result.status is AnchorStatus.DOCUMENT_UNAVAILABLE for result in results)


def test_a_tampered_cached_file_fails_its_hash(dataset, tmp_path):
    cache, sha256 = _dataset_with_pdf(dataset, tmp_path)
    cache.path_for(sha256).write_bytes(b"%PDF-1.7 tampered")
    results = verify_dataset(dataset, cache, None)
    assert results and all(result.status is AnchorStatus.HASH_MISMATCH for result in results)


def test_a_document_changed_at_source_is_reported_not_silently_accepted(dataset, tmp_path):
    cache = Cache(tmp_path / "cache")
    document = dataset.documents["report-q1"]

    def web(url: str, headers: dict) -> HttpResponse:
        if url.endswith("robots.txt"):
            return HttpResponse(404, {}, b"", url)
        return HttpResponse(200, {"content-type": "application/pdf"}, b"%PDF-1.7 revised", url)

    fetcher = Fetcher(dataset.sources.values(), cache, http_get=web, sleep=lambda _: None)
    results = verify_dataset(dataset, cache, fetcher)
    assert document.sha256 == "a" * 64
    assert results and all(result.status is AnchorStatus.HASH_MISMATCH for result in results)
    assert "source now serves" in results[0].detail


def test_an_isin_printed_but_not_transcribed_is_found(dataset, tmp_path):
    extra = "INE501X07620"
    cache, _ = _dataset_with_pdf(dataset, tmp_path, text=f"{ISIN_LISTED} and {extra}")
    assert untranscribed_isins(dataset, cache, None) == [("report-q1", extra)]


def test_a_partial_transcription_is_not_checked_for_missing_isins(dataset, tmp_path):
    cache, _ = _dataset_with_pdf(dataset, tmp_path, text=f"{ISIN_LISTED} and INE501X07620")
    dataset.breach_reports["report-q1"] = make_report(
        rows=[make_row()], extraction_complete=False, visually_reviewed=False
    )
    assert untranscribed_isins(dataset, cache, None) == []


def test_the_audit_flags_text_drawn_as_vector_outlines(tmp_path):
    glyphs = b" ".join(b"0 0 m 1 1 2 2 3 3 c f" for _ in range(600))
    pdf = write_pdf(tmp_path / "outlined.pdf", [glyphs])
    page = audit_text_layer(pdf)[0]
    assert page.curve_segments == 600
    assert "outlines" in page.problem


def test_the_audit_passes_ruled_tables_and_ordinary_text(tmp_path):
    ruled = b" ".join(b"0 0 m 100 100 l S" for _ in range(600)) + b" " + text_stream("a real text layer with words")
    assert audit_text_layer(write_pdf(tmp_path / "ruled.pdf", [ruled]))[0].problem is None


def test_text_layer_warnings_name_document_and_page(dataset, tmp_path):
    glyphs = b" ".join(b"0 0 m 1 1 2 2 3 3 c f" for _ in range(600))
    pdf = write_pdf(tmp_path / "outlined.pdf", [text_stream("ordinary"), glyphs])
    cache = Cache(tmp_path / "cache")
    sha256, _ = cache.store(pdf.read_bytes(), {})
    dataset.documents["report-q1"] = make_document(sha256=sha256)
    warnings = text_layer_warnings(dataset, cache)
    assert [(document, page) for document, page, _ in warnings] == [("report-q1", 2)]


def test_file_hash_matches_the_cache_key(tmp_path):
    cache = Cache(tmp_path)
    sha256, path = cache.store(b"content", {})
    assert file_sha256(path) == sha256
