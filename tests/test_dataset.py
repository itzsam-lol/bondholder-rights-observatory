"""Checks on the published dataset itself, which must hold whenever the records change."""

import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from brdo import models
from brdo.build import tables
from brdo.census import check_census
from brdo.dictionary import datapackage, render_markdown, undocumented
from brdo.fetch import Cache, Fetcher, default_cache_dir
from brdo.identifiers import is_valid_isin
from brdo.pit import as_of, availability
from brdo.report import render_report
from brdo.status import StatusBasis, derive_all, trustees_claimed
from brdo.store import check_integrity, load_dataset
from brdo.verify import AnchorStatus, load_document_text, verify_dataset
from brdo.vocab import (
    AvailabilityMode,
    CoverageStatus,
    RedistributionPolicy,
    RetrievalPolicy,
    SearchOutcome,
    SearchPurpose,
    SourceKind,
)

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
    published = [path for path in (REPOSITORY / "data").rglob("*.yaml") if path.name != "sources.yaml"]
    published += [*(REPOSITORY / "exports").iterdir(), *(REPOSITORY / "docs").glob("*.md")]
    for path in published:
        assert "nseindia" not in path.read_text(encoding="utf-8").lower(), path.name


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


def test_a_listed_isin_is_a_reported_breach_unless_an_explicit_statement_disagrees(data):
    statuses = {(s.isin, s.period_end): s for s in derive_all(data)}
    conflicting = set()
    for report in data.breach_reports.values():
        for row in report.rows:
            for isin in row.isins:
                status = statuses[(isin, report.period.end)]
                if status.status is CoverageStatus.CONFLICTING:
                    assert status.basis is StatusBasis.STATEMENTS_DISAGREE
                    conflicting.add(isin)
                else:
                    assert status.status is CoverageStatus.REPORTED_BREACH
    assert conflicting == {"INE00VD07016", "INE00VD07032"}


def test_a_breach_stated_only_by_the_issuer_is_still_a_reported_breach(data):
    status = next(s for s in derive_all(data) if s.isin == "INE982X08042" and s.period_end == date(2026, 6, 30))
    assert (status.status, status.basis) == (CoverageStatus.REPORTED_BREACH, StatusBasis.EXPLICIT_STATEMENT)


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


def _cutoffs(data) -> list[date]:
    """Every day on which some document's availability changes under either mode, and the day before it."""
    days = set()
    for document in data.documents.values():
        found = availability(document, data)
        days |= {day for day in (found.estimate, found.observed) if day is not None}
    return sorted({day + timedelta(days=offset) for day in days for offset in (-1, 0)})


@pytest.mark.parametrize("mode", list(AvailabilityMode))
def test_no_point_in_time_view_holds_anything_later_than_its_date(data, mode):
    for day in _cutoffs(data):
        view = as_of(data, day, mode)
        for document in view.documents.values():
            found = availability(document, data)
            shown = found.observed if mode is AvailabilityMode.OBSERVED else found.estimate
            assert shown is not None and shown <= day, (day, document.id)
        for label, item in view.evidence():
            assert item.document in view.documents, (day, label, item.document)
        observations = [o for i in view.instruments.values() for c in i.claims for o in c.observations]
        observations += [o for i in view.issuers.values() for o in i.observations]
        observations += [o for d in view.discrepancies.values() for o in d.observations]
        assert all(o.observed_on <= day for o in observations), day
        found_reports = {
            (s.subject, s.period.end)
            for s in view.searches.values()
            if s.purpose is SearchPurpose.TRUSTEE_REPORT and s.outcome is SearchOutcome.FOUND and s.period
        }
        for status in derive_all(view):
            assert set(status.documents) <= set(view.documents), (day, status)
            if status.basis is StatusBasis.TRUSTEE_REPORT_NOT_SEARCHED:
                trustees = trustees_claimed(view, status.isin)
                assert not {(t, status.period_end) for t in trustees} & found_reports, (day, status)


def test_the_full_record_is_the_view_as_of_the_last_retrieval(data):
    last = max(d.retrieved_at.date() for d in data.documents.values() if d.retrieved_at)
    for mode in AvailabilityMode:
        view = as_of(data, last, mode)
        assert set(view.documents) == set(data.documents)
        assert derive_all(view) == derive_all(data)


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


def test_every_exported_column_is_documented(data):
    assert undocumented(tables(data)) == []


def test_the_committed_data_package_matches_the_exports(data):
    on_disk = json.loads((REPOSITORY / "exports" / "datapackage.json").read_text(encoding="utf-8"))
    assert on_disk == datapackage(tables(data)), "exports/datapackage.json is stale; run `brdo build`"


def test_the_committed_data_dictionary_matches_the_code():
    on_disk = (REPOSITORY / "docs" / "data-dictionary.md").read_text(encoding="utf-8")
    assert on_disk == render_markdown(), "docs/data-dictionary.md is stale; run `brdo dictionary`"


def test_quotations_are_marked_as_such_in_the_data_package(data):
    """A reader of the flat files must be able to tell every quoted column from the project's own work."""
    package = datapackage(tables(data))
    kinds = {
        (resource["path"], field["name"]): field["brdo:kind"]
        for resource in package["resources"]
        for field in resource["schema"]["fields"]
    }
    quoted = {key for key, kind in kinds.items() if kind == "source_text"}
    assert ("breach_report_items.csv", "covenant_as_reported") in quoted
    assert ("evidence.csv", "quote") in quoted
    assert all(name.endswith("_as_reported") or name in {"text", "quote", "heading"} for _, name in quoted)
    assert {key for key in kinds if key[1].endswith("_as_reported")} <= quoted


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


def test_every_census_reproduces_from_its_cached_file(data):
    cache = Cache(REPOSITORY / default_cache_dir())
    checked = 0
    for census in data.monitoring_censuses.values():
        text = load_document_text(data.documents[census.document], cache, None)
        if text.pages is None:
            continue
        assert check_census(data, census, text.pages) == [], census.id
        checked += 1
    if not checked:
        pytest.skip("no census file is in the local cache; run `brdo fetch`")


_PERSONAL_DATA = {
    "e-mail address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "depository participant id": re.compile(r"\bIN\d{6}\b"),
    "PAN": re.compile(r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b"),
    "phone number": re.compile(r"\+91[\s-]?[6-9]\d{4}[\s-]?\d{5}\b|\b[6-9]\d{4}\s\d{5}\b"),
}


def test_published_records_hold_no_personal_identifiers():
    """Bare ten-digit numbers are not checked: they cannot be told apart from rupee amounts."""
    paths = [*(REPOSITORY / "data").rglob("*.yaml"), *(REPOSITORY / "exports").glob("*.csv")]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for kind, pattern in _PERSONAL_DATA.items():
            assert not pattern.search(text), f"{path.name} contains what looks like a {kind}"


@pytest.mark.network
def test_sources_still_serve_the_recorded_files(data):
    cache = Cache(REPOSITORY / default_cache_dir())
    fetcher = Fetcher(data.sources.values(), cache)
    results = verify_dataset(data, cache, fetcher)
    assert not [r for r in results if r.status is AnchorStatus.HASH_MISMATCH]
