"""A point-in-time view must hold only what was public by its date, and say how availability is known."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from brdo.models import BreachNotice, Claim, Discrepancy, DocumentDate, Evidence, Observation, SearchRecord
from brdo.pit import OWN_DATE_BASIS, as_of, availability, available_from
from brdo.status import StatusBasis, derive_status, trustees_claimed
from brdo.store import Severity, check_integrity
from brdo.vocab import (
    AvailabilityMode,
    CoverageStatus,
    DateBasis,
    DiscrepancyKind,
    DocumentDateKind,
    InstrumentProperty,
    SearchChannel,
    SearchOutcome,
    SearchPurpose,
)
from tests.conftest import ISIN_LISTED, ISIN_UNLISTED, QUARTER, make_document, make_source, trustee_claim


def _dated(kind: DocumentDateKind, day: date, basis: DateBasis) -> DocumentDate:
    return DocumentDate(kind=kind, value=day, basis=basis)


LAST_MODIFIED = DocumentDateKind.LAST_MODIFIED
HEADER = DateBasis.HTTP_LAST_MODIFIED


def test_a_server_header_cannot_be_recorded_as_a_publication_date():
    with pytest.raises(ValidationError, match="last_modified"):
        _dated(DocumentDateKind.PUBLISHED, date(2026, 8, 3), HEADER)
    with pytest.raises(ValidationError):
        _dated(LAST_MODIFIED, date(2026, 8, 3), DateBasis.LISTING_PAGE)


def test_a_server_date_is_preferred_to_the_documents_own_date():
    document = make_document(
        dates=[
            _dated(DocumentDateKind.DATED, date(2026, 7, 2), DateBasis.STATED_IN_DOCUMENT),
            _dated(LAST_MODIFIED, date(2026, 8, 3), HEADER),
        ]
    )
    assert available_from(document) == (date(2026, 8, 3), "http_last_modified")
    assert availability(document).not_before == date(2026, 7, 2)


def test_the_later_of_the_publishers_and_the_servers_date_is_taken():
    listed = _dated(DocumentDateKind.PUBLISHED, date(2026, 9, 13), DateBasis.LISTING_PAGE)
    replaced_later = make_document(dates=[listed, _dated(LAST_MODIFIED, date(2026, 9, 20), HEADER)])
    uploaded_earlier = make_document(dates=[listed, _dated(LAST_MODIFIED, date(2026, 9, 1), HEADER)])
    same_day = make_document(dates=[listed, _dated(LAST_MODIFIED, date(2026, 9, 13), HEADER)])
    assert available_from(replaced_later) == (date(2026, 9, 20), "http_last_modified")
    assert available_from(uploaded_earlier) == (date(2026, 9, 13), "listing_page")
    assert available_from(same_day) == (date(2026, 9, 13), "listing_page")


def test_a_documents_own_date_is_only_a_lower_bound():
    document = make_document(dates=[_dated(DocumentDateKind.DATED, date(2026, 7, 2), DateBasis.STATED_IN_DOCUMENT)])
    assert available_from(document) == (date(2026, 7, 2), OWN_DATE_BASIS)


def test_a_server_date_before_the_documents_own_date_gives_way_and_is_reported(dataset):
    document = make_document(
        dates=[
            _dated(DocumentDateKind.DATED, date(2026, 8, 20), DateBasis.STATED_IN_DOCUMENT),
            _dated(LAST_MODIFIED, date(2026, 8, 3), HEADER),
        ]
    )
    assert available_from(document) == (date(2026, 8, 20), OWN_DATE_BASIS)
    dataset.documents["report-q1"] = document
    warnings = [p for p in check_integrity(dataset) if p.severity is Severity.WARNING and "precedes" in p.message]
    assert warnings


def test_a_date_after_retrieval_is_an_error(dataset):
    dataset.documents["report-q1"] = make_document(
        retrieved_at=datetime(2026, 9, 1, tzinfo=UTC), dates=[_dated(LAST_MODIFIED, date(2026, 9, 5), HEADER)]
    )
    errors = [p for p in check_integrity(dataset) if p.severity is Severity.ERROR and "retrieved" in p.message]
    assert errors


def test_a_letter_in_the_file_bounds_its_availability_from_below(dataset):
    dataset.documents["notices"] = make_document("notices", dates=[_dated(LAST_MODIFIED, date(2026, 8, 1), HEADER)])
    dataset.breach_notices["n1"] = BreachNotice(
        id="n1",
        document="notices",
        page=1,
        trustee="trustee-a",
        isins=[ISIN_LISTED],
        issued_on=date(2026, 8, 9),
    )
    found = availability(dataset.documents["notices"], dataset)
    assert found.not_before == date(2026, 8, 9)
    assert (found.estimate, found.estimate_basis) == (date(2026, 8, 9), OWN_DATE_BASIS)


def test_a_retrieved_file_with_no_other_date_is_public_from_its_retrieval():
    document = make_document(retrieved_at=datetime(2026, 11, 3, 7, 54, tzinfo=UTC))
    assert available_from(document) == (date(2026, 11, 3), "observed by the project")


def test_a_document_of_unknown_availability_is_left_out(dataset):
    assert available_from(dataset.documents["report-q1"]) == (None, "unknown")
    assert not as_of(dataset, date(2030, 1, 1)).breach_reports


def test_a_report_published_after_the_date_does_not_count(dataset):
    dataset.documents["report-q1"] = make_document(dates=[_dated(LAST_MODIFIED, date(2026, 9, 13), HEADER)])
    before, after = as_of(dataset, date(2026, 9, 12)), as_of(dataset, date(2026, 9, 13))
    assert derive_status(before, ISIN_LISTED, QUARTER.end).status is not CoverageStatus.REPORTED_BREACH
    assert derive_status(after, ISIN_LISTED, QUARTER.end).status is CoverageStatus.REPORTED_BREACH


def test_the_observed_mode_counts_a_file_only_from_its_retrieval(dataset):
    dataset.documents["report-q1"] = make_document(
        retrieved_at=datetime(2026, 11, 3, 7, 54, tzinfo=UTC), dates=[_dated(LAST_MODIFIED, date(2026, 9, 13), HEADER)]
    )
    assert as_of(dataset, date(2026, 10, 1)).breach_reports
    observed = as_of(dataset, date(2026, 10, 1), AvailabilityMode.OBSERVED)
    assert not observed.breach_reports
    assert as_of(dataset, date(2026, 11, 3), AvailabilityMode.OBSERVED).breach_reports


def test_a_claim_supported_only_by_a_later_document_is_left_out(dataset):
    dataset.documents["report-q1"] = make_document(dates=[_dated(LAST_MODIFIED, date(2026, 9, 13), HEADER)])
    view = as_of(dataset, date(2026, 9, 1))
    assert not view.instruments[ISIN_LISTED].claims
    assert trustees_claimed(view, ISIN_LISTED) == set()
    assert derive_status(view, ISIN_LISTED, QUARTER.end).basis is StatusBasis.TRUSTEE_UNKNOWN


def test_a_claim_keeps_only_the_evidence_that_was_public(dataset):
    dataset.documents["early"] = make_document("early", dates=[_dated(LAST_MODIFIED, date(2026, 5, 1), HEADER)])
    dataset.documents["report-q1"] = make_document(dates=[_dated(LAST_MODIFIED, date(2026, 9, 13), HEADER)])
    both = Claim(
        property=InstrumentProperty.DEBENTURE_TRUSTEE,
        value="trustee-a",
        asserted_by="trustee-a",
        evidence=[Evidence(document="early", page=1, quote=ISIN_LISTED), trustee_claim().evidence[0]],
    )
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [both]})
    claim = as_of(dataset, date(2026, 6, 1)).instruments[ISIN_LISTED].claims[0]
    assert [item.document for item in claim.evidence] == ["early"]


def test_an_observation_counts_only_from_the_day_it_was_made(dataset):
    dataset.sources["depository"] = make_source("depository")
    seen = Observation(url="https://depository.example/isin", observed_on=date(2026, 11, 3), value_seen="TRUSTEE A")
    claim = Claim(
        property=InstrumentProperty.DEBENTURE_TRUSTEE, value="trustee-a", asserted_by="depository", observations=[seen]
    )
    dataset.instruments[ISIN_UNLISTED] = dataset.instruments[ISIN_UNLISTED].model_copy(update={"claims": [claim]})
    dataset.discrepancies["d1"] = Discrepancy(
        id="d1", kind=DiscrepancyKind.IDENTITY, subject=ISIN_UNLISTED, description="x", observations=[seen]
    )
    before = as_of(dataset, date(2026, 11, 2))
    assert not before.instruments[ISIN_UNLISTED].claims and not before.discrepancies
    after = as_of(dataset, date(2026, 11, 3))
    assert after.instruments[ISIN_UNLISTED].claims and after.discrepancies


def test_a_report_found_later_is_not_yet_public_rather_than_not_searched(dataset):
    dataset.documents["report-q1"] = make_document(dates=[_dated(LAST_MODIFIED, date(2026, 9, 13), HEADER)])
    early_claim = Claim(
        property=InstrumentProperty.DEBENTURE_TRUSTEE,
        value="trustee-a",
        asserted_by="trustee-a",
        evidence=[Evidence(document="letter", page=1, quote=ISIN_LISTED)],
    )
    dataset.documents["letter"] = make_document("letter", dates=[_dated(LAST_MODIFIED, date(2026, 5, 6), HEADER)])
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [early_claim]})
    dataset.searches["s1"] = SearchRecord(
        id="s1",
        performed_on=date(2026, 11, 3),
        subject="trustee-a",
        purpose=SearchPurpose.TRUSTEE_REPORT,
        channel=SearchChannel.SOURCE_LISTING_PAGE,
        period=QUARTER,
        outcome=SearchOutcome.FOUND,
        documents=["report-q1"],
    )
    status = derive_status(as_of(dataset, date(2026, 9, 1)), ISIN_LISTED, QUARTER.end)
    assert (status.status, status.basis) == (CoverageStatus.NO_REPORT_FOUND, StatusBasis.TRUSTEE_REPORT_NOT_YET_PUBLIC)
    assert status.documents == ()
    full = derive_status(dataset, ISIN_LISTED, QUARTER.end)
    assert full.status is CoverageStatus.REPORTED_BREACH


def test_a_view_of_a_view_keeps_the_earlier_cutoff_and_everything_withheld(dataset):
    dataset.documents["report-q1"] = make_document(dates=[_dated(LAST_MODIFIED, date(2026, 9, 13), HEADER)])
    once = as_of(dataset, date(2026, 9, 1))
    twice = as_of(once, date(2026, 12, 1))
    assert twice.cutoff == date(2026, 9, 1)
    assert "report-q1" in twice.withheld and not twice.breach_reports
