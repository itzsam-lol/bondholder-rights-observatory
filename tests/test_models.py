from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from brdo.models import (
    MAX_QUOTE_CHARS,
    BreachNotice,
    Claim,
    Discrepancy,
    Document,
    Evidence,
    Intimation,
    Period,
    Provision,
    ReportedDate,
    SearchRecord,
    StatedException,
    Threshold,
)
from brdo.vocab import (
    Comparator,
    CovenantCategory,
    DiscrepancyKind,
    DiscrepancyStatus,
    DocumentType,
    InstrumentProperty,
    ProvisionStage,
    Recipient,
    SearchChannel,
    SearchOutcome,
    SearchPurpose,
    ThresholdUnit,
)
from tests.conftest import ISIN_LISTED, make_document, make_report, make_row, make_statement


def test_quotes_are_capped_so_the_dataset_only_holds_short_quotations():
    Evidence(document="d", page=1, quote="x" * MAX_QUOTE_CHARS)
    with pytest.raises(ValidationError):
        Evidence(document="d", page=1, quote="x" * (MAX_QUOTE_CHARS + 1))


def test_unknown_fields_are_rejected_rather_than_ignored():
    with pytest.raises(ValidationError):
        Evidence(document="d", page=1, quote="abc", pagee=2)


def test_a_recorded_date_must_agree_with_the_printed_text():
    assert ReportedDate(raw="22-07-26", value=date(2026, 7, 22)).value == date(2026, 7, 22)
    with pytest.raises(ValidationError, match="reads as"):
        ReportedDate(raw="22-07-26", value=date(2026, 7, 23))


def test_a_value_read_from_unparseable_text_must_be_explained():
    with pytest.raises(ValidationError, match="needs a note"):
        ReportedDate(raw="30th September, 2023 till date", value=date(2023, 9, 30))
    ReportedDate(raw="30th September, 2023 till date", value=date(2023, 9, 30), note="Start of a continuing default.")


def test_a_claim_needs_some_support():
    with pytest.raises(ValidationError, match="neither evidence nor an observation"):
        Claim(property=InstrumentProperty.DEBENTURE_TRUSTEE, value="t", asserted_by="t")


def test_a_period_cannot_run_backwards():
    with pytest.raises(ValidationError):
        Period(start=date(2026, 6, 30), end=date(2026, 4, 1))


def test_a_retrieved_document_must_have_a_hash():
    with pytest.raises(ValidationError, match="SHA-256"):
        make_document(sha256=None, retrieved_at=datetime(2026, 1, 1, tzinfo=UTC))


def test_a_document_cannot_supersede_itself():
    with pytest.raises(ValidationError):
        make_document("r", supersedes=["r"])


def test_a_report_cannot_claim_completeness_without_visual_review():
    with pytest.raises(ValidationError, match="rendered pages"):
        make_report(visually_reviewed=False)
    assert make_report(extraction_complete=False, visually_reviewed=False).extraction_complete is False


def test_a_nil_report_cannot_list_rows():
    with pytest.raises(ValidationError, match="nil report"):
        make_report(nil_report=True)
    assert make_report(nil_report=True, rows=[]).nil_report


def test_an_empty_report_must_say_it_is_nil():
    with pytest.raises(ValidationError, match="nil_report"):
        make_report(rows=[])


def test_a_threshold_needs_a_named_metric():
    threshold = Threshold(comparator=Comparator.LT, value=5, unit=ThresholdUnit.PERCENT)
    fields = dict(
        id="p",
        document="d",
        clause="1",
        page=1,
        text="abc",
        instruments=["INE501X07588"],
        category=CovenantCategory.FINANCIAL,
    )
    with pytest.raises(ValidationError, match="metric"):
        Provision(**fields, thresholds=[threshold])
    assert Provision(**fields, thresholds=[threshold], metric="Ratio").thresholds


def test_invalid_isins_are_rejected_at_the_schema_level():
    with pytest.raises(ValidationError, match="invalid ISIN"):
        Provision(
            id="p",
            document="d",
            clause="1",
            page=1,
            text="abc",
            instruments=["INE501X07589"],
            category=CovenantCategory.OTHER,
        )


def test_a_successful_search_must_name_what_it_found():
    fields = dict(
        id="s",
        performed_on=date(2026, 11, 4),
        subject="INE501X07588",
        purpose=SearchPurpose.CONTRACT_DOCUMENT,
        channel=SearchChannel.WEB_SEARCH,
    )
    with pytest.raises(ValidationError, match="must name"):
        SearchRecord(**fields, outcome=SearchOutcome.FOUND)
    assert SearchRecord(**fields, outcome=SearchOutcome.NOT_FOUND).documents == []


def test_a_resolved_discrepancy_must_say_how():
    fields = dict(id="d", kind=DiscrepancyKind.VALUE, subject="x", description="y", status=DiscrepancyStatus.RESOLVED)
    with pytest.raises(ValidationError, match="how it was resolved"):
        Discrepancy(**fields)
    assert Discrepancy(**fields, resolution="Source corrected.").resolution


def test_row_anchors_cover_what_the_row_says_was_printed():
    row = make_row().model_copy(
        update={"further_action_as_reported": "Awaiting instructions", "delay_reasons_as_reported": "NA"}
    )
    quotes = {anchor.quote for anchor in row.anchors("doc")}
    assert {
        "maintain a ratio of less than 5%",
        "INE501X07588",
        "Example Finance Limited",
        "30-06-26",
        "14-08-26",
        "Awaiting instructions",
    } <= quotes
    assert "NA" not in quotes


def test_rows_read_from_the_rendering_allow_visual_fallback_on_every_anchor():
    row = make_row().model_copy(update={"transcribed_from_rendering": True})
    assert all(anchor.visual_fallback for anchor in row.anchors("doc"))


def test_notice_anchors_skip_isins_the_notice_does_not_print():
    fields = dict(id="n", document="d", page=1, trustee="t", isins=["INE501X07588"], issued_on=date(2026, 1, 1))
    assert {a.quote for a in BreachNotice(**fields).anchors()} == {"INE501X07588"}
    assert not list(BreachNotice(**fields, isins_printed=False).anchors())


def test_a_notice_cannot_record_a_deed_date_its_quote_does_not_print():
    fields = dict(id="n", document="d", page=1, trustee="t", isins=["INE501X07588"], issued_on=date(2026, 1, 1))
    quote = "Debenture Trust Deed dated 16 th May, 2024"
    assert BreachNotice(**fields, deed_as_reported=quote, deed_dates=[date(2024, 5, 16)]).deed_dates
    with pytest.raises(ValidationError, match="deed_dates"):
        BreachNotice(**fields, deed_as_reported=quote, deed_dates=[date(2024, 5, 17)])


def test_a_notice_cannot_record_an_intimation_date_its_quote_does_not_print():
    fields = dict(id="n", document="d", page=1, trustee="t", isins=["INE501X07588"], issued_on=date(2026, 1, 1))
    quote = "received intimation from the issuer on 22 nd July, 2026"
    assert BreachNotice(**fields, issuer_intimation=date(2026, 7, 22), issuer_intimation_as_reported=quote)
    with pytest.raises(ValidationError, match="issuer_intimation"):
        BreachNotice(**fields, issuer_intimation=date(2026, 7, 23), issuer_intimation_as_reported=quote)


def test_a_row_cannot_record_an_intimation_date_it_does_not_print():
    row = make_row().model_dump()
    row.update(
        intimation_as_reported="CRAs & SEBI - 27-Jul-26",
        intimations=[{"recipients": [Recipient.SEBI], "dated": date(2026, 7, 28)}],
    )
    with pytest.raises(ValidationError, match="not printed"):
        make_row().model_validate(row)
    assert Intimation(recipients=[Recipient.SEBI], dated=date(2026, 7, 27))


def test_document_types_are_a_closed_vocabulary():
    with pytest.raises(ValidationError):
        Document(id="d", source="s", type="brochure", title="t", url="https://x.example")
    assert DocumentType.TRUSTEE_BREACH_STATUS_REPORT.value == "trustee_breach_status_report"


def test_a_statement_listing_exceptions_must_state_a_breach():
    line = StatedException(isins=[ISIN_LISTED], page=1, covenant_as_reported="Cost to Income Ratio")
    with pytest.raises(ValidationError, match="does not state a breach"):
        make_statement(breach=False, exceptions=[line])


def test_exceptions_may_only_name_the_statements_own_instruments():
    line = StatedException(isins=["INE501X07570"], page=1, covenant_as_reported="Cost to Income Ratio")
    with pytest.raises(ValidationError, match="not among its instruments"):
        make_statement(breach=True, exceptions=[line])


def test_every_exception_field_becomes_a_checkable_anchor():
    line = StatedException(
        isins=[ISIN_LISTED], page=8, covenant_as_reported="Cost to Income Ratio", required_as_reported="<=85%"
    )
    quotes = {anchor.quote for anchor in make_statement(breach=True, exceptions=[line]).anchors()}
    assert {ISIN_LISTED, "Cost to Income Ratio", "<=85%"} <= quotes


def test_a_clause_record_is_a_description_unless_said_otherwise():
    provision = Provision(
        id="p",
        document="d",
        clause="1",
        page=1,
        text="maintain a ratio",
        instruments=[ISIN_LISTED],
        category="financial",
    )
    assert provision.stage is ProvisionStage.DESCRIBED_IN_FORCE
