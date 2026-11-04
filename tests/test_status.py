"""The categories in the status vocabulary must stay distinct; absence must never read as compliance."""

from datetime import date

from brdo.models import BreachNotice, ComplianceStatement, NoInformationEntry, SearchRecord
from brdo.status import StatusBasis, derive_all, derive_status, reporting_periods
from brdo.vocab import (
    CovenantCategory,
    CoverageStatus,
    NoticeKind,
    SearchChannel,
    SearchOutcome,
    SearchPurpose,
    StatementScope,
)
from tests.conftest import (
    ISIN_LISTED,
    ISIN_UNLISTED,
    QUARTER,
    make_document,
    make_report,
    make_row,
    make_source,
    make_statement,
    trustee_claim,
)

PERIOD_END = QUARTER.end


def _statement(identifier: str, breach: bool, isin: str = ISIN_UNLISTED, **options) -> ComplianceStatement:
    return make_statement(identifier, breach=breach, isin=isin, **options)


def test_listed_in_the_current_report_is_a_reported_breach(dataset):
    result = derive_status(dataset, ISIN_LISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.REPORTED_BREACH, StatusBasis.LISTED_IN_CURRENT_VERSION)
    assert result.documents == ("report-q1",)


def test_absent_from_a_complete_report_is_no_report_found_and_never_compliance(dataset):
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.NO_REPORT_FOUND, StatusBasis.NOT_LISTED_IN_TRUSTEE_REPORT)
    assert result.status is not CoverageStatus.REPORTED_NO_BREACH


def test_a_nil_table_is_also_only_no_report_found(dataset):
    dataset.breach_reports["report-q1"] = make_report(nil_report=True, rows=[])
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.NO_REPORT_FOUND, StatusBasis.TRUSTEE_REPORT_IS_NIL)


def test_only_an_explicit_statement_gives_reported_no_breach(dataset):
    dataset.compliance_statements["s"] = _statement("s", breach=False)
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.REPORTED_NO_BREACH, StatusBasis.EXPLICIT_STATEMENT)


def test_a_statement_of_compliance_does_not_override_a_listing(dataset):
    dataset.compliance_statements["s"] = _statement("s", breach=False, isin=ISIN_LISTED)
    result = derive_status(dataset, ISIN_LISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.CONFLICTING, StatusBasis.STATEMENTS_DISAGREE)


def test_a_statement_limited_to_financial_covenants_does_not_answer_a_listing_of_another_kind(dataset):
    row = make_row()
    item = row.items[0].model_copy(update={"category": CovenantCategory.AFFIRMATIVE})
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    dataset.compliance_statements["s"] = _statement(
        "s", breach=False, isin=ISIN_LISTED, scope=StatementScope.FINANCIAL_COVENANTS
    )
    result = derive_status(dataset, ISIN_LISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.REPORTED_BREACH, StatusBasis.LISTED_IN_CURRENT_VERSION)


def test_a_statement_limited_to_financial_covenants_contradicts_a_financial_listing(dataset):
    dataset.compliance_statements["s"] = _statement(
        "s", breach=False, isin=ISIN_LISTED, scope=StatementScope.FINANCIAL_COVENANTS
    )
    result = derive_status(dataset, ISIN_LISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.CONFLICTING, StatusBasis.STATEMENTS_DISAGREE)


def test_disagreeing_statements_stay_conflicting(dataset):
    dataset.compliance_statements["a"] = _statement("a", breach=False)
    dataset.compliance_statements["b"] = _statement("b", breach=True)
    assert derive_status(dataset, ISIN_UNLISTED, PERIOD_END).status is CoverageStatus.CONFLICTING


def test_a_listing_dropped_by_a_later_version_is_conflicting_not_cleared(dataset):
    dataset.documents["report-v2"] = make_document("report-v2", supersedes=["report-q1"])
    dataset.breach_reports["report-v2"] = make_report("report-v2", rows=[make_row(ISIN_UNLISTED)])
    result = derive_status(dataset, ISIN_LISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.CONFLICTING, StatusBasis.LISTED_ONLY_IN_EARLIER_VERSION)


def test_only_the_current_version_counts_for_a_listing(dataset):
    dataset.documents["report-v2"] = make_document("report-v2", supersedes=["report-q1"])
    dataset.breach_reports["report-v2"] = make_report("report-v2")
    assert derive_status(dataset, ISIN_LISTED, PERIOD_END).documents == ("report-v2",)


def test_a_listing_that_depends_on_reading_merged_cells_is_ambiguous(dataset):
    dataset.breach_reports["report-q1"] = make_report(rows=[make_row(uncertain=True)])
    result = derive_status(dataset, ISIN_LISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.AMBIGUOUS, StatusBasis.LISTING_DEPENDS_ON_LAYOUT)


def test_a_row_labelled_for_an_earlier_quarter_keeps_its_own_basis(dataset):
    dataset.breach_reports["report-q1"] = make_report(rows=[make_row(carried=date(2026, 3, 31))])
    assert derive_status(dataset, ISIN_LISTED, PERIOD_END).basis is StatusBasis.LISTED_AS_CARRIED_OVER


def test_no_information_from_the_issuer_is_its_own_category(dataset):
    dataset.breach_reports["report-q1"] = make_report(
        rows=[make_row()],
        no_information=[
            NoInformationEntry(issuer_name_as_reported="Example Finance Limited", issuer="example-finance", page=1)
        ],
    )
    assert derive_status(dataset, ISIN_UNLISTED, PERIOD_END).status is CoverageStatus.NO_INFORMATION_REPORTED


def test_a_partly_transcribed_report_supports_no_inference_from_absence(dataset):
    dataset.breach_reports["report-q1"] = make_report(extraction_complete=False, visually_reviewed=False)
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (
        CoverageStatus.NOT_ASSESSED,
        StatusBasis.TRUSTEE_REPORT_INCOMPLETELY_TRANSCRIBED,
    )


def test_an_unknown_trustee_means_not_assessed(dataset):
    dataset.instruments[ISIN_UNLISTED] = dataset.instruments[ISIN_UNLISTED].model_copy(update={"claims": []})
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.NOT_ASSESSED, StatusBasis.TRUSTEE_UNKNOWN)


def test_disputed_trustee_identity_blocks_inference_from_absence(dataset):
    dataset.sources["trustee-b"] = make_source("trustee-b")
    instrument = dataset.instruments[ISIN_UNLISTED]
    dataset.instruments[ISIN_UNLISTED] = instrument.model_copy(
        update={"claims": [trustee_claim(), trustee_claim("trustee-b")]}
    )
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.AMBIGUOUS, StatusBasis.TRUSTEE_NOT_ESTABLISHED)


def _report_search(outcome: SearchOutcome) -> SearchRecord:
    return SearchRecord(
        id="s",
        performed_on=date(2026, 11, 4),
        subject="trustee-a",
        purpose=SearchPurpose.TRUSTEE_REPORT,
        channel=SearchChannel.SOURCE_LISTING_PAGE,
        period=QUARTER,
        outcome=outcome,
    )


def test_a_report_that_could_not_be_reached_is_inaccessible(dataset):
    dataset.breach_reports.clear()
    dataset.searches["s"] = _report_search(SearchOutcome.ACCESS_ERROR)
    assert derive_status(dataset, ISIN_UNLISTED, PERIOD_END).status is CoverageStatus.INACCESSIBLE


def test_a_report_excluded_by_policy_is_inaccessible(dataset):
    dataset.breach_reports.clear()
    dataset.searches["s"] = _report_search(SearchOutcome.EXCLUDED_BY_POLICY)
    assert derive_status(dataset, ISIN_UNLISTED, PERIOD_END).status is CoverageStatus.INACCESSIBLE


def test_failing_to_find_a_report_keeps_a_distinct_basis_from_reading_one(dataset):
    dataset.breach_reports.clear()
    dataset.searches["s"] = _report_search(SearchOutcome.NOT_FOUND)
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.NO_REPORT_FOUND, StatusBasis.TRUSTEE_REPORT_NOT_LOCATED)


def test_nobody_having_looked_is_not_assessed(dataset):
    dataset.breach_reports.clear()
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.NOT_ASSESSED, StatusBasis.TRUSTEE_REPORT_NOT_SEARCHED)


def _notice(kind: NoticeKind = NoticeKind.BREACH) -> BreachNotice:
    return BreachNotice(
        id="n",
        document="report-q1",
        page=1,
        trustee="trustee-a",
        kind=kind,
        isins=[ISIN_UNLISTED],
        issued_on=date(2026, 8, 1),
        period_end=PERIOD_END,
    )


def test_a_trustee_notice_is_enough_to_record_a_reported_breach(dataset):
    dataset.breach_notices["n"] = _notice()
    result = derive_status(dataset, ISIN_UNLISTED, PERIOD_END)
    assert (result.status, result.basis) == (CoverageStatus.REPORTED_BREACH, StatusBasis.NAMED_IN_TRUSTEE_NOTICE)


def test_a_meeting_continuation_letter_is_not_itself_a_report_of_breach(dataset):
    dataset.breach_notices["n"] = _notice(NoticeKind.MEETING_CONTINUATION)
    assert derive_status(dataset, ISIN_UNLISTED, PERIOD_END).status is CoverageStatus.NO_REPORT_FOUND


def test_every_period_with_any_record_is_derived_for_every_instrument(dataset):
    dataset.breach_notices["n"] = _notice().model_copy(update={"period_end": date(2026, 3, 31)})
    assert reporting_periods(dataset) == [date(2026, 3, 31), PERIOD_END]
    assert len(derive_all(dataset)) == 2 * len(dataset.instruments)
