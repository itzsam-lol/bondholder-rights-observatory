"""Checks on the published dataset itself, which must hold whenever the records change."""

import csv
import json
from datetime import date
from pathlib import Path

import pytest

from brdo import models
from brdo.build import tables
from brdo.fetch import Cache, Fetcher, default_cache_dir
from brdo.identifiers import is_valid_isin
from brdo.report import render_report
from brdo.status import derive_all
from brdo.store import check_integrity, load_dataset
from brdo.verify import AnchorStatus, verify_dataset
from brdo.vocab import CoverageStatus, RedistributionPolicy, RetrievalPolicy, SourceKind

REPOSITORY = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def data():
    return load_dataset(REPOSITORY / "data")


def test_the_dataset_has_no_integrity_errors_or_warnings(data):
    assert [str(problem) for problem in check_integrity(data)] == []


def test_every_isin_passes_its_check_digit(data):
    assert all(is_valid_isin(isin) for isin in data.instruments)


def test_nothing_from_nse_is_cited_or_linked(data):
    nse = data.sources["nse"]
    assert nse.retrieval is RetrievalPolicy.EXCLUDED and nse.redistribution is RedistributionPolicy.NO_LINKS
    assert not [d.id for d in data.documents.values() if d.source == "nse"]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPOSITORY / "data").rglob("*.yaml")
        if path.name != "sources.yaml"
    )
    assert "nseindia" not in text.lower()


def test_nothing_from_depositories_or_platforms_was_retrieved_by_the_pipeline(data):
    closed = {s.id for s in data.sources.values() if s.retrieval is not RetrievalPolicy.ALLOWED}
    assert not [d.id for d in data.documents.values() if d.source in closed and not d.retrieved_manually]


def test_no_source_document_is_committed():
    tracked_suffixes = {path.suffix.lower() for path in (REPOSITORY / "data").rglob("*") if path.is_file()}
    assert tracked_suffixes <= {".yaml"}


def test_every_reported_breach_points_at_documents(data):
    for status in derive_all(data):
        if status.status is CoverageStatus.REPORTED_BREACH:
            assert status.documents, status


def test_every_listed_isin_has_status_reported_breach_for_its_report_period(data):
    statuses = {(s.isin, s.period_end): s for s in derive_all(data)}
    for report in data.breach_reports.values():
        for row in report.rows:
            for isin in row.isins:
                assert statuses[(isin, report.period.end)].status is CoverageStatus.REPORTED_BREACH


def test_trustees_named_in_reports_are_registered_as_such(data):
    for report in data.breach_reports.values():
        assert data.sources[report.trustee].kind is SourceKind.DEBENTURE_TRUSTEE


def test_restricted_trustee_text_is_only_quoted_in_short_anchors(data):
    report_rows = [row for report in data.breach_reports.values() for row in report.rows]
    assert all(len(item.covenant_as_reported) <= 160 for row in report_rows for item in row.items)
    assert all(len(row.further_action_as_reported or "") <= 160 for row in report_rows)


def test_cut_cells_say_so(data):
    items = [item for report in data.breach_reports.values() for row in report.rows for item in row.items]
    cut = [item for item in items if item.truncated]
    assert cut and all(len(item.covenant_as_reported) > 100 for item in cut)


def test_numbers_in_cut_cells_survive_as_facts(data):
    item = next(
        item
        for row in data.breach_reports["ctl-t5-2026-06"].rows
        for item in row.items
        if "INE982X08091" in item.isins and item.covenant_as_reported.startswith("As per Clause 9.3")
    )
    assert {"17%", "15%", "3%", "870crores", "5.00%"} <= set(item.levels_stated)


def test_every_breach_report_was_reviewed_on_its_rendered_pages(data):
    assert all(report.visually_reviewed and report.extraction_complete for report in data.breach_reports.values())


def test_axis_versions_are_chained_and_show_the_reported_waiver(data):
    later = data.documents["axis-t5-2026-06-v20260916"]
    assert later.supersedes == ["axis-t5-2026-06-v20260814"]
    row = data.breach_reports["axis-t5-2026-06-v20260916"].rows[0]
    assert row.further_action_as_reported.startswith("Waiver has been received")


def test_amended_clauses_keep_their_earlier_text(data):
    revised = data.provisions["aye-ine501x07620-par90-revised"]
    earlier = data.provisions[revised.amends]
    assert earlier.thresholds[0].value == 8
    assert [threshold.value for threshold in revised.thresholds] == [12, 10]


def test_one_isin_can_have_many_deeds(data):
    deeds = {d for notice in data.breach_notices.values() if "INE982X08109" in notice.isins for d in notice.deed_dates}
    assert len(deeds) == 5


def test_covenants_differ_within_an_issuer(data):
    first = data.provisions["aye-ine501x07588-clause-10-3-a"]
    second = data.provisions["aye-ine501x07570-clause-9-3-a-viii"]
    assert (first.thresholds[0].value, first.metric) != (second.thresholds[0].value, second.metric)


def test_absence_from_a_report_is_recorded_as_no_report_found(data):
    statuses = {(s.isin, s.period_end): s for s in derive_all(data)}
    assert statuses[("INE501X07570", date(2026, 3, 31))].status is CoverageStatus.REPORTED_BREACH
    assert statuses[("INE501X07570", date(2026, 6, 30))].status is CoverageStatus.NO_REPORT_FOUND


def test_committed_exports_match_the_records(data):
    for name, rows in tables(data).items():
        path = REPOSITORY / "exports" / f"{name}.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            on_disk = list(csv.DictReader(handle))
        expected = [{key: str(value) for key, value in row.items()} for row in rows]
        assert on_disk == expected, f"{path} is stale; run `brdo build`"


def test_the_committed_report_matches_the_records(data):
    assert (REPOSITORY / "docs" / "observability-report.md").read_text(encoding="utf-8") == render_report(data)


def test_committed_schemas_match_the_models():
    for path in (REPOSITORY / "schema").glob("*.json"):
        record = getattr(models, path.stem)
        assert json.loads(path.read_text(encoding="utf-8")) == json.loads(json.dumps(record.model_json_schema())), path


def test_every_anchor_verifies_against_the_cached_sources(data):
    cache = Cache(REPOSITORY / default_cache_dir())
    if not any(cache.get(d.sha256) for d in data.documents.values() if d.sha256):
        pytest.skip("source documents are not in the local cache; run `brdo fetch`")
    results = verify_dataset(data, cache, None)
    failures = [r for r in results if not r.ok and r.status is not AnchorStatus.DOCUMENT_UNAVAILABLE]
    assert not failures, failures[:5]


@pytest.mark.network
def test_sources_still_serve_the_recorded_files(data):
    cache = Cache(REPOSITORY / default_cache_dir())
    fetcher = Fetcher(data.sources.values(), cache)
    results = verify_dataset(data, cache, fetcher)
    assert not [r for r in results if r.status is AnchorStatus.HASH_MISMATCH]
