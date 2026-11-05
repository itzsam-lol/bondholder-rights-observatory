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
    ComplianceStatement,
    Discrepancy,
    DocumentDate,
    Evidence,
    Issuer,
    NameVariant,
    Observation,
    SearchRecord,
)
from brdo.pit import NO_ESTIMATE_BASIS, OWN_DATE_BASIS, as_of, availability, match_name, placeholder_issuer, supports
from brdo.status import StatusBasis, derive_status, trustees_claimed
from brdo.store import Severity, check_integrity
from brdo.vocab import (
    AvailabilityMode,
    AvailabilityState,
    CoverageStatus,
    DateBasis,
    DiscrepancyKind,
    DocumentDateKind,
    InstrumentProperty,
    SearchChannel,
    SearchOutcome,
    SearchPurpose,
    SourceKind,
    StatementMaker,
    StatementScope,
    SupportBasis,
)
from tests.conftest import (
    ISIN_LISTED,
    ISIN_UNLISTED,
    QUARTER,
    make_document,
    make_report,
    make_row,
    make_source,
    trustee_claim,
)

LAST_MODIFIED = DocumentDateKind.LAST_MODIFIED
HEADER = DateBasis.HTTP_LAST_MODIFIED
NOVEMBER = datetime(2026, 11, 3, 7, 54, tzinfo=UTC)


OBSERVED, ESTIMATED, POSSIBLE = AvailabilityMode.OBSERVED, AvailabilityMode.ESTIMATED, AvailabilityMode.POSSIBLE
OTHER_ISIN = "INE179P07530"


def _dated(kind: DocumentDateKind, day: date, basis: DateBasis) -> DocumentDate:
    return DocumentDate(kind=kind, value=day, basis=basis)


def _estimate(document, dataset=None):
    found = availability(document, dataset)
    return found.estimate, found.estimate_basis


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
    assert _estimate(replaced_later) == (date(2026, 9, 20), "http_last_modified")
    assert _estimate(uploaded_earlier) == (date(2026, 9, 13), "listing_page")
    assert _estimate(same_day) == (date(2026, 9, 13), "listing_page")


def test_a_documents_own_date_is_only_a_lower_bound_and_never_an_estimate():
    document = make_document(dates=[_dated(DocumentDateKind.DATED, date(2026, 7, 2), DateBasis.STATED_IN_DOCUMENT)])
    found = availability(document)
    assert (found.not_before, found.estimate, found.estimate_basis) == (date(2026, 7, 2), None, NO_ESTIMATE_BASIS)
    assert found.confirmed_by is None
    assert found.state_on(date(2026, 7, 1)) is AvailabilityState.NOT_YET_POSSIBLE
    assert found.state_on(date(2030, 1, 1)) is AvailabilityState.UNCERTAIN


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
    assert _estimate(document) == (date(2026, 8, 20), OWN_DATE_BASIS)
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


def test_a_retrieved_file_with_no_publisher_or_server_date_has_no_estimate():
    found = availability(make_document(retrieved_at=NOVEMBER, period=None))
    assert (found.estimate, found.estimate_basis) == (None, NO_ESTIMATE_BASIS)
    assert found.admitted_from(ESTIMATED) == found.admitted_from(OBSERVED) == date(2026, 11, 3)
    assert found.admitted_from(POSSIBLE) == date.min  # nothing rules it out on any earlier day


def test_a_document_of_unknown_availability_is_left_out(dataset):
    dataset.breach_reports["report-q1"] = dataset.breach_reports["report-q1"].model_copy(update={"rows": []})
    dataset.breach_reports["report-q1"] = dataset.breach_reports["report-q1"].model_copy(update={"nil_report": True})
    assert _estimate(dataset.documents["report-q1"], dataset) == (None, NO_ESTIMATE_BASIS)
    assert not as_of(dataset, date(2030, 1, 1)).breach_reports
    assert not as_of(dataset, date(2030, 1, 1), OBSERVED).breach_reports
    # Only the period it reports on bounds it, so the upper envelope admits it from the period's start.
    assert not as_of(dataset, date(2026, 3, 31), POSSIBLE).breach_reports
    assert as_of(dataset, date(2026, 4, 1), POSSIBLE).breach_reports


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
    seen = Observation(
        url=f"https://depository.example/bond?ISIN={ISIN_UNLISTED}",
        observed_on=date(2026, 11, 3),
        value_seen="TRUSTEE A",
    )
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


# --- Availability as states, and three nested views ---


def test_each_day_is_ruled_out_uncertain_or_confirmed():
    document = make_document(
        retrieved_at=NOVEMBER,
        dates=[
            _dated(DocumentDateKind.DATED, date(2026, 8, 1), DateBasis.STATED_IN_DOCUMENT),
            _dated(LAST_MODIFIED, date(2026, 9, 13), HEADER),
        ],
    )
    found = availability(document)
    assert found.state_on(date(2026, 7, 31)) is AvailabilityState.NOT_YET_POSSIBLE
    assert found.state_on(date(2026, 8, 1)) is AvailabilityState.UNCERTAIN
    # A server's date is not evidence that the file was public on it.
    assert found.state_on(date(2026, 9, 13)) is AvailabilityState.UNCERTAIN
    assert found.state_on(date(2026, 11, 3)) is AvailabilityState.CONFIRMED


def test_the_three_views_nest_and_record_each_files_state(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13), retrieved_at=NOVEMBER)
    # The fixture's row prints a detection on 14 August, so the report cannot have been public before then.
    assert not as_of(dataset, date(2026, 8, 13), POSSIBLE).breach_reports
    on = {mode: as_of(dataset, date(2026, 9, 1), mode) for mode in (OBSERVED, ESTIMATED, POSSIBLE)}
    assert not on[OBSERVED].breach_reports and not on[ESTIMATED].breach_reports
    assert on[POSSIBLE].availability_states == {"report-q1": AvailabilityState.UNCERTAIN}
    assert as_of(dataset, date(2026, 9, 13)).availability_states == {"report-q1": AvailabilityState.UNCERTAIN}
    for mode in (OBSERVED, ESTIMATED, POSSIBLE):
        assert as_of(dataset, date(2026, 11, 3), mode).availability_states == {"report-q1": AvailabilityState.CONFIRMED}


def test_a_view_never_reveals_when_the_project_later_observed_a_file(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13), retrieved_at=NOVEMBER)
    view = as_of(dataset, date(2026, 10, 1))
    assert set(view.availability_states.values()) == {AvailabilityState.UNCERTAIN}
    assert view.documents["report-q1"].retrieved_at is None


def test_a_view_keeps_no_retrieval_or_server_date_from_after_its_day(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13), retrieved_at=NOVEMBER)
    possible = as_of(dataset, date(2026, 9, 1), POSSIBLE).documents["report-q1"]
    assert possible.retrieved_at is None and possible.dates == []
    estimated = as_of(dataset, date(2026, 10, 1)).documents["report-q1"]
    assert [held.value for held in estimated.dates] == [date(2026, 9, 13)]
    observed = as_of(dataset, date(2026, 11, 3), OBSERVED).documents["report-q1"]
    assert observed.retrieved_at == NOVEMBER


# --- What establishes an ISIN, whose it is, and an issuer ---


def test_a_claims_evidence_establishes_an_isin_only_where_its_quotation_prints_it(dataset):
    claim = trustee_claim().model_copy(
        update={"evidence": [Evidence(document="report-q1", page=1, quote="Trustee A Limited")]}
    )
    dataset.instruments[ISIN_UNLISTED] = dataset.instruments[ISIN_UNLISTED].model_copy(update={"claims": [claim]})
    assert not [s for s in supports(dataset) if s.key == ISIN_UNLISTED and s.attribute == "identity"]
    assert ISIN_UNLISTED not in as_of(dataset, date(2030, 1, 1)).instruments


def test_a_letter_printing_only_the_isin_does_not_show_whose_it_is(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.documents["letter"] = make_document("letter", dates=[_dated(LAST_MODIFIED, date(2026, 5, 6), HEADER)])
    dataset.breach_notices["n1"] = BreachNotice(
        id="n1", document="letter", page=1, trustee="trustee-a", isins=[ISIN_LISTED], issued_on=date(2026, 5, 5)
    )
    [letter] = [s for s in supports(dataset) if s.attribute == "issuer" and s.record == "letter n1"]
    assert letter.basis is SupportBasis.LETTER_TO_HOLDERS and not letter.establishes
    early = as_of(dataset, date(2026, 6, 1))
    assert ISIN_LISTED in early.instruments and early.relationship_bases[ISIN_LISTED] is None
    assert early.instruments[ISIN_LISTED].issuer == placeholder_issuer("501X")
    assert "example-finance" not in early.issuers
    later = as_of(dataset, date(2026, 9, 13))
    assert later.relationship_bases[ISIN_LISTED] is SupportBasis.PRINTED_WITH_NAME
    assert later.instruments[ISIN_LISTED].issuer == "example-finance"


def test_an_isin_takes_its_issuer_from_its_code_only_if_no_other_issuer_uses_that_code(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    view = as_of(dataset, date(2026, 9, 13))
    assert view.relationship_bases[ISIN_LISTED] is SupportBasis.PRINTED_WITH_NAME
    assert view.relationship_bases[ISIN_UNLISTED] is SupportBasis.ISSUER_CODE
    dataset.issuers["other"] = Issuer(id="other", name="Other Finance Limited")
    dataset.instruments[ISIN_UNLISTED] = dataset.instruments[ISIN_UNLISTED].model_copy(update={"issuer": "other"})
    assert as_of(dataset, date(2026, 9, 13)).relationship_bases[ISIN_UNLISTED] is None


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("Aye Finance Limited", SupportBasis.EXACT_NAME),
        ("AYE FINANCE LTD.", SupportBasis.EXACT_NAME),
        ("Aye Finance Limited (formerly known as Aye Finance Private Limited)", SupportBasis.NAME_WITH_ADDITION),
        ("Aye Finance Limited (AFL)", SupportBasis.NAME_WITH_ADDITION),
        ("Aye Finance Pvt Ltd", SupportBasis.NAME_VARIANT),
        ("Finance Limited", None),
        ("Aye Finance Limited Holdings", None),
        ("New Aye Finance Limited", None),
        ("Aye Finance", None),
    ],
)
def test_names_match_as_whole_names_never_by_containment(printed, expected):
    issuer = Issuer(
        id="aye",
        name="Aye Finance Limited",
        name_variants=[
            NameVariant(name="Aye Finance Private Limited", evidence=[Evidence(document="d", page=1, quote="x" * 3)])
        ],
    )
    assert match_name(printed, issuer) is expected


def _second_issuer_of_the_same_name(dataset, observed: bool = False):
    """Two issuers printed under one name, told apart only by CINs seen on depository pages."""
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    cins = {"example-finance": "U65990TN2014PTC096252", "example-finance-2": "U65990TN2021PTC146392"}
    isins = {"example-finance": ISIN_LISTED, "example-finance-2": OTHER_ISIN}
    for issuer_id, cin in cins.items():
        pages = [
            Observation(
                url=f"https://depository.example/bond?ISIN={isins[issuer_id]}",
                observed_on=date(2026, 11, 3),
                value_seen=f"EXAMPLE FINANCE LIMITED; CIN {cin}",
            )
        ]
        dataset.issuers[issuer_id] = Issuer(
            id=issuer_id, name="Example Finance Limited", cin=cin, observations=pages if observed else []
        )
    dataset.instruments[OTHER_ISIN] = dataset.instruments[ISIN_UNLISTED].model_copy(
        update={"isin": OTHER_ISIN, "issuer": "example-finance-2", "claims": []}
    )
    second = make_row(OTHER_ISIN).model_copy(update={"row": "2", "issuer": "example-finance-2"})
    dataset.breach_reports["report-q1"] = make_report(rows=[make_row(), second])


def test_issuers_of_one_name_are_not_told_apart_without_an_identifier(dataset):
    _second_issuer_of_the_same_name(dataset)
    view = as_of(dataset, date(2026, 10, 1))
    assert set(view.issuers) == {placeholder_issuer("501X"), placeholder_issuer("179P")}
    assert {view.instruments[i].issuer for i in (ISIN_LISTED, OTHER_ISIN)} == set(view.issuers)
    assert all(issuer.name == "Example Finance Limited" for issuer in view.issuers.values())
    rows = view.breach_reports["report-q1"].rows
    assert {row.issuer for row in rows} == set(view.issuers)


def test_an_identifier_seen_later_tells_them_apart_from_that_day(dataset):
    _second_issuer_of_the_same_name(dataset, observed=True)
    assert set(as_of(dataset, date(2026, 11, 2)).issuers) == {placeholder_issuer("501X"), placeholder_issuer("179P")}
    after = as_of(dataset, date(2026, 11, 3))
    assert set(after.issuers) == {"example-finance", "example-finance-2"}
    assert after.issuers["example-finance-2"].cin == "U65990TN2021PTC146392"


def test_a_cin_counts_only_from_the_issuers_own_publication_or_a_quotation_naming_it(dataset):
    cin = "U65921DL1993PLC283660"
    dataset.sources["issuer-web"] = make_source("issuer-web", kind=SourceKind.ISSUER, issuer="example-finance")
    dataset.documents["own"] = make_document(
        "own", source="issuer-web", dates=[_dated(LAST_MODIFIED, date(2026, 5, 1), HEADER)]
    )
    dataset.issuers["example-finance"] = Issuer(id="example-finance", name="Example Finance Limited", cin=cin)
    dataset.discrepancies["elsewhere"] = Discrepancy(
        id="elsewhere",
        kind=DiscrepancyKind.IDENTITY,
        subject=ISIN_LISTED,
        description="x",
        evidence=[Evidence(document="report-q1", page=1, quote=f"CIN: {cin}")],
    )
    assert not [s for s in supports(dataset) if s.attribute == "cin"]
    dataset.discrepancies["own"] = Discrepancy(
        id="own",
        kind=DiscrepancyKind.IDENTITY,
        subject=ISIN_LISTED,
        description="x",
        evidence=[Evidence(document="own", page=1, quote=f"CIN: {cin}")],
    )
    [found] = [s for s in supports(dataset) if s.attribute == "cin"]
    assert found.basis is SupportBasis.ISSUER_PUBLICATION and found.document == "own"


def test_the_issuers_own_website_shows_whose_isin_it_is_but_not_its_name(dataset):
    dataset.sources["issuer-web"] = make_source("issuer-web", kind=SourceKind.ISSUER, issuer="example-finance")
    dataset.documents["own"] = make_document(
        "own", source="issuer-web", dates=[_dated(LAST_MODIFIED, date(2026, 5, 1), HEADER)]
    )
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.compliance_statements["s"] = ComplianceStatement(
        id="s",
        document="own",
        instruments=[ISIN_LISTED],
        period=QUARTER,
        stated_by="issuer-web",
        made_by=StatementMaker.ISSUER,
        scope=StatementScope.ALL_COVENANTS,
        breach_stated=False,
        evidence=[Evidence(document="own", page=1, quote=f"{ISIN_LISTED} complied")],
    )
    view = as_of(dataset, date(2026, 6, 1))
    assert view.relationship_bases[ISIN_LISTED] is SupportBasis.ISSUER_PUBLICATION
    assert view.instruments[ISIN_LISTED].issuer == "example-finance"
    assert view.issuers["example-finance"].name == ""


def test_a_view_drops_later_descriptions_and_isins_no_admitted_record_prints(dataset):
    dataset.documents["report-q1"] = _modified(date(2026, 9, 13))
    dataset.documents["letter"] = make_document("letter", dates=[_dated(LAST_MODIFIED, date(2026, 5, 6), HEADER)])
    dataset.breach_notices["n1"] = BreachNotice(
        id="n1",
        document="letter",
        page=1,
        trustee="trustee-a",
        isins=[ISIN_LISTED],
        issued_on=date(2026, 5, 5),
        isins_printed=False,
    )
    dataset.discrepancies["d"] = Discrepancy(
        id="d",
        kind=DiscrepancyKind.VALUE,
        subject=ISIN_LISTED,
        description="Written in November.",
        evidence=[Evidence(document="report-q1", page=1, quote="x" * 3)],
    )
    early = as_of(dataset, date(2026, 6, 1))
    assert "n1" not in early.breach_notices  # its only ISIN is printed by no record admitted by then
    later = as_of(dataset, date(2026, 9, 13))
    assert later.breach_notices["n1"].isins == [ISIN_LISTED]
    assert later.discrepancies["d"].description == ""
