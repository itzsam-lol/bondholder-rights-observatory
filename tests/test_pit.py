"""A point-in-time view must hold only what records public by its date establish, and say how availability is known.

These tests show that the rules are applied consistently. They cannot show that the dates the rules rely on are
historically right.
"""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from brdo.models import (
    BreachNotice,
    Claim,
    Discrepancy,
    DocumentDate,
    Evidence,
    Issuer,
    NameVariant,
    Observation,
    SearchRecord,
)
from brdo.pit import CONFIRMED_BASIS, OWN_DATE_BASIS, as_of, availability, available_from, supports
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

LAST_MODIFIED = DocumentDateKind.LAST_MODIFIED
HEADER = DateBasis.HTTP_LAST_MODIFIED
NOVEMBER = datetime(2026, 11, 3, 7, 54, tzinfo=UTC)


def _dated(kind: DocumentDateKind, day: date, basis: DateBasis) -> DocumentDate:
    return DocumentDate(kind=kind, value=day, basis=basis)


def _modified(day: date, **overrides):
    return make_document(dates=[_dated(LAST_MODIFIED, day, HEADER)], **overrides)


def _trustee_search(found: list[str], outcome=SearchOutcome.FOUND, on=date(2026, 11, 3)) -> SearchRecord:
    return SearchRecord(
        id="s1",
        performed_on=on,
        subject="trustee-a",
        purpose=SearchPurpose.TRUSTEE_REPORT,
        channel=SearchChannel.SOURCE_LISTING_PAGE,
        period=QUARTER,
        outcome=outcome,
        documents=found,
    )


def _early_claim(document: str = "letter") -> Claim:
    return Claim(
        property=InstrumentProperty.DEBENTURE_TRUSTEE,
        value="trustee-a",
        asserted_by="trustee-a",
        evidence=[Evidence(document=document, page=1, quote=ISIN_LISTED)],
    )


# --- The evidence on availability, kept apart ---


def test_a_server_header_cannot_be_recorded_as_a_publication_date():
    with pytest.raises(ValidationError, match="last_modified"):
        _dated(DocumentDateKind.PUBLISHED, date(2026, 8, 3), HEADER)
    with pytest.raises(ValidationError):
        _dated(LAST_MODIFIED, date(2026, 8, 3), DateBasis.LISTING_PAGE)


def test_a_server_date_is_preferred_to_the_documents_own_date_but_never_called_publication():
    document = make_document(
        dates=[
            _dated(DocumentDateKind.DATED, date(2026, 7, 2), DateBasis.STATED_IN_DOCUMENT),
            _dated(LAST_MODIFIED, date(2026, 8, 3), HEADER),
        ]
    )
    found = availability(document)
    assert (found.estimate, found.estimate_basis) == (date(2026, 8, 3), "http_last_modified")
    assert (found.not_before, found.not_before_basis) == (date(2026, 7, 2), "its own date")
    assert found.published is None


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
    assert availability(document).confirmed_by is None


def test_retrieval_confirms_availability_and_closes_the_window(dataset):
    document = make_document(
        retrieved_at=NOVEMBER,
        dates=[
            _dated(DocumentDateKind.DATED, date(2026, 8, 1), DateBasis.STATED_IN_DOCUMENT),
            _dated(LAST_MODIFIED, date(2026, 9, 13), HEADER),
        ],
    )
    found = availability(document)
    assert (found.not_before, found.estimate, found.confirmed_by) == (
        date(2026, 8, 1),
        date(2026, 9, 13),
        date(2026, 11, 3),
    )
    assert found.confirmed_basis == "retrieved by pipeline"
    assert found.window_days == 94


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
    dataset.documents["report-q1"] = _modified(date(2026, 11, 5), retrieved_at=NOVEMBER)
    errors = [p for p in check_integrity(dataset) if p.severity is Severity.ERROR and "retrieved" in p.message]
    assert errors


def test_a_letter_in_the_file_bounds_its_availability_from_below(dataset):
    dataset.documents["notices"] = make_document("notices", dates=[_dated(LAST_MODIFIED, date(2026, 8, 1), HEADER)])
    dataset.breach_notices["n1"] = BreachNotice(
        id="n1", document="notices", page=1, trustee="trustee-a", isins=[ISIN_LISTED], issued_on=date(2026, 8, 9)
    )
    found = availability(dataset.documents["notices"], dataset)
    assert (found.not_before, found.not_before_basis) == (date(2026, 8, 9), "a letter it contains")
    assert (found.estimate, found.estimate_basis) == (date(2026, 8, 9), "not before a letter it contains")


def test_an_event_a_report_prints_bounds_it_from_below(dataset):
    # The fixture's row prints a detection on 14 August 2026, so the report cannot have been public before then.
    found = availability(dataset.documents["report-q1"], dataset)
    assert (found.not_before, found.not_before_basis) == (date(2026, 8, 14), "an event it reports")


def test_a_retrieved_file_with_no_other_date_is_public_from_its_retrieval():
    assert available_from(make_document(retrieved_at=NOVEMBER)) == (date(2026, 11, 3), CONFIRMED_BASIS)


def test_a_document_of_unknown_availability_is_left_out(dataset):
    dataset.breach_reports["report-q1"] = dataset.breach_reports["report-q1"].model_copy(update={"rows": []})
    dataset.breach_reports["report-q1"] = dataset.breach_reports["report-q1"].model_copy(update={"nil_report": True})
    assert available_from(dataset.documents["report-q1"], dataset) == (None, "unknown")
    assert not as_of(dataset, date(2030, 1, 1)).breach_reports


# --- Records, entities and attributes ---


def test_a_report_published_after_the_date_does_not_count(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    before, after = as_of(dataset, date(2026, 9, 12)), as_of(dataset, date(2026, 9, 13))
    assert ISIN_LISTED not in before.instruments
    assert derive_status(after, ISIN_LISTED, QUARTER.end).status is CoverageStatus.REPORTED_BREACH


def test_the_observed_mode_counts_a_file_only_from_its_retrieval(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13), retrieved_at=NOVEMBER)
    assert as_of(dataset, date(2026, 10, 1)).breach_reports
    assert not as_of(dataset, date(2026, 10, 1), AvailabilityMode.OBSERVED).breach_reports
    assert as_of(dataset, date(2026, 11, 3), AvailabilityMode.OBSERVED).breach_reports


def test_an_instrument_appears_only_when_a_record_printing_its_isin_is_public(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    view = as_of(dataset, date(2026, 9, 1))
    assert not view.instruments and not view.issuers
    later = as_of(dataset, date(2026, 9, 13))
    assert set(later.instruments) == {ISIN_LISTED, ISIN_UNLISTED} and set(later.issuers) == {"example-finance"}


def test_a_claim_keeps_only_the_evidence_that_was_public(dataset):
    dataset.documents["early"] = make_document("early", dates=[_dated(LAST_MODIFIED, date(2026, 5, 1), HEADER)])
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    both = _early_claim("early").model_copy(
        update={"evidence": [*_early_claim("early").evidence, *trustee_claim().evidence]}
    )
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [both]})
    view = as_of(dataset, date(2026, 6, 1))
    [claim] = view.instruments[ISIN_LISTED].claims
    assert [item.document for item in claim.evidence] == ["early"]
    assert ISIN_UNLISTED not in view.instruments


def test_an_issuers_identifiers_need_a_public_record_that_prints_them(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    seen = Observation(
        url="https://depository.example/isin", observed_on=date(2026, 11, 3), value_seen="LEI 335800Q6CHM9LTEPY552"
    )
    dataset.issuers["example-finance"] = Issuer(
        id="example-finance",
        name="Example Finance Limited",
        cin="U65921DL1993PLC283660",
        lei="335800Q6CHM9LTEPY552",
        sector="lending",
        observations=[seen],
    )
    view = as_of(dataset, date(2026, 10, 1))
    issuer = view.issuers["example-finance"]
    assert (issuer.cin, issuer.lei, issuer.sector) == (None, None, None)
    assert issuer.name == "Example Finance Limited"  # printed in the report's row
    assert as_of(dataset, date(2026, 11, 3)).issuers["example-finance"].lei == "335800Q6CHM9LTEPY552"


def test_an_issuer_whose_name_is_not_yet_printed_takes_the_name_then_printed(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.documents["early"] = make_document("early", dates=[_dated(LAST_MODIFIED, date(2026, 5, 1), HEADER)])
    dataset.issuers["example-finance"] = Issuer(
        id="example-finance",
        name="Example Finance Limited",
        name_variants=[
            NameVariant(
                name="Example Finance Private Limited", evidence=[Evidence(document="early", page=1, quote="x" * 3)]
            )
        ],
    )
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(
        update={"claims": [_early_claim("early")]}
    )
    issuer = as_of(dataset, date(2026, 6, 1)).issuers["example-finance"]
    assert issuer.name == "Example Finance Private Limited"


def test_an_observation_counts_only_from_the_day_it_was_made(dataset):
    dataset.sources["depository"] = make_source("depository")
    seen = Observation(url="https://depository.example/isin", observed_on=date(2026, 11, 3), value_seen="TRUSTEE A")
    claim = Claim(
        property=InstrumentProperty.DEBENTURE_TRUSTEE, value="trustee-a", asserted_by="depository", observations=[seen]
    )
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.instruments[ISIN_UNLISTED] = dataset.instruments[ISIN_UNLISTED].model_copy(update={"claims": [claim]})
    dataset.discrepancies["d1"] = Discrepancy(
        id="d1", kind=DiscrepancyKind.IDENTITY, subject=ISIN_UNLISTED, description="x", observations=[seen]
    )
    before = as_of(dataset, date(2026, 11, 2))
    assert ISIN_UNLISTED not in before.instruments and not before.discrepancies
    after = as_of(dataset, date(2026, 11, 3))
    assert after.instruments[ISIN_UNLISTED].claims and after.discrepancies


def test_notes_written_with_later_knowledge_are_dropped(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(
        update={"notes": "Listed again in the trustee's December report."}
    )
    view = as_of(dataset, date(2026, 9, 13))
    assert view.instruments[ISIN_LISTED].notes is None
    assert all(claim.note is None for claim in view.instruments[ISIN_LISTED].claims)


# --- Searches never decide what was public ---


def test_a_later_search_is_not_in_the_view_and_proves_nothing_about_earlier_availability(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.documents["letter"] = make_document("letter", dates=[_dated(LAST_MODIFIED, date(2026, 5, 6), HEADER)])
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [_early_claim()]})
    dataset.searches["s1"] = _trustee_search(["report-q1"])
    view = as_of(dataset, date(2026, 9, 1))
    assert not view.searches
    estimated = derive_status(view, ISIN_LISTED, QUARTER.end)
    assert (estimated.status, estimated.basis) == (CoverageStatus.NOT_ASSESSED, StatusBasis.TRUSTEE_REPORT_NOT_IN_VIEW)
    assert estimated.documents == ()
    assert not hasattr(view, "withheld")


def test_the_observed_view_says_the_project_had_not_looked(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13), retrieved_at=datetime(2026, 11, 4, tzinfo=UTC))
    dataset.documents["letter"] = make_document("letter", retrieved_at=NOVEMBER)
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [_early_claim()]})
    dataset.searches["s1"] = _trustee_search(["report-q1"], on=date(2026, 11, 4))
    view = as_of(dataset, date(2026, 11, 3), AvailabilityMode.OBSERVED)
    status = derive_status(view, ISIN_LISTED, QUARTER.end)
    assert (status.status, status.basis) == (CoverageStatus.NOT_ASSESSED, StatusBasis.TRUSTEE_REPORT_NOT_SEARCHED)


def test_a_failed_search_made_by_the_date_still_counts_as_of_its_own_date(dataset):
    dataset.documents["letter"] = make_document("letter", dates=[_dated(LAST_MODIFIED, date(2026, 5, 6), HEADER)])
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(update={"claims": [_early_claim()]})
    dataset.breach_reports.clear()
    dataset.searches["s1"] = _trustee_search([], outcome=SearchOutcome.NOT_FOUND, on=date(2026, 8, 1))
    status = derive_status(as_of(dataset, date(2026, 9, 1)), ISIN_LISTED, QUARTER.end)
    assert (status.status, status.basis) == (CoverageStatus.NO_REPORT_FOUND, StatusBasis.TRUSTEE_REPORT_NOT_LOCATED)


def test_a_claim_supported_only_by_a_later_document_is_left_out(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.documents["letter"] = make_document("letter", dates=[_dated(LAST_MODIFIED, date(2026, 5, 6), HEADER)])
    early = _early_claim().model_copy(update={"property": InstrumentProperty.LISTING_EXCHANGE, "value": "BSE"})
    dataset.instruments[ISIN_LISTED] = dataset.instruments[ISIN_LISTED].model_copy(
        update={"claims": [early, trustee_claim()]}
    )
    view = as_of(dataset, date(2026, 9, 1))
    assert trustees_claimed(view, ISIN_LISTED) == set()
    assert derive_status(view, ISIN_LISTED, QUARTER.end).basis is StatusBasis.TRUSTEE_UNKNOWN


def test_a_view_of_a_view_keeps_the_earlier_cutoff(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    twice = as_of(as_of(dataset, date(2026, 9, 1)), date(2026, 12, 1))
    assert twice.cutoff == date(2026, 9, 1)
    assert not twice.breach_reports


def test_every_support_names_its_document_or_observation(dataset):
    for support in supports(dataset):
        assert (support.document is None) != (support.observation is None), support
