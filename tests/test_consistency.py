from datetime import date

from brdo.consistency import (
    compare_notices_with_reports,
    compare_statements_with_reports,
    revisions,
    stated_thresholds,
)
from brdo.models import BreachNotice, DocumentDate, StatedException
from brdo.vocab import Agreement, CovenantCategory, DateBasis, DocumentDateKind, StatementScope
from tests.conftest import (
    ISIN_LISTED,
    ISIN_UNLISTED,
    QUARTER,
    make_document,
    make_report,
    make_row,
    make_statement,
)


def test_thresholds_are_read_regardless_of_spacing_and_case():
    text = "ratio less than 5 % and 2.85X cover, net worth of Rs. 870 Crores, CAR 17%"
    assert stated_thresholds(text) == {"5%", "2.85x", "870crores", "17%"}


def test_clause_numbers_are_not_mistaken_for_thresholds():
    assert stated_thresholds("As per Clause 2.5.3 (viii) of the deed dated 2024") == frozenset()


def _notice(**overrides) -> BreachNotice:
    values = dict(
        id="n",
        document="report-q1",
        page=1,
        trustee="trustee-a",
        isins=[ISIN_LISTED],
        issued_on=date(2026, 8, 16),
        period_end=QUARTER.end,
        issuer_intimation=date(2026, 8, 14),
        covenant_as_reported="maintain a ratio of less than 5%",
        levels_stated=["5%"],
    )
    return BreachNotice(**(values | overrides))


def test_a_notice_that_agrees_with_the_report_compares_clean(dataset):
    dataset.breach_notices["n"] = _notice()
    comparison = compare_notices_with_reports(dataset)[0]
    assert comparison.days_from_intimation_to_detection == 0
    assert comparison.thresholds_agree is True


def test_differing_dates_and_levels_are_surfaced(dataset):
    dataset.breach_notices["n"] = _notice(issuer_intimation=date(2026, 8, 11), levels_stated=["6%"])
    comparison = compare_notices_with_reports(dataset)[0]
    assert comparison.days_from_intimation_to_detection == 3
    assert comparison.thresholds_agree is False


def test_a_notice_stating_no_level_has_nothing_to_compare(dataset):
    dataset.breach_notices["n"] = _notice(covenant_as_reported="breach of financial covenant", levels_stated=[])
    assert compare_notices_with_reports(dataset)[0].thresholds_agree is None


def test_a_passage_only_partly_read_is_not_compared_as_if_whole(dataset):
    dataset.breach_notices["n"] = _notice(levels_complete=False)
    assert compare_notices_with_reports(dataset)[0].thresholds_agree is None


def test_a_notice_without_a_matching_report_row_is_skipped(dataset):
    dataset.breach_notices["n"] = _notice(period_end=date(2026, 3, 31))
    assert compare_notices_with_reports(dataset) == []


def test_a_notice_that_prints_no_isin_is_not_compared(dataset):
    dataset.breach_notices["n"] = _notice(isins_printed=False)
    assert compare_notices_with_reports(dataset) == []


def test_comparison_uses_the_current_version_of_a_report(dataset):
    dataset.documents["report-v2"] = make_document("report-v2", supersedes=["report-q1"])
    dataset.breach_reports["report-v2"] = make_report("report-v2")
    dataset.breach_notices["n"] = _notice()
    assert compare_notices_with_reports(dataset)[0].report == "report-v2"


def test_a_changed_action_between_versions_is_a_revision(dataset):
    first = make_row().model_copy(update={"further_action_as_reported": "Seeking instructions"})
    second = make_row().model_copy(update={"further_action_as_reported": "Waiver received"})
    dataset.breach_reports["report-q1"] = make_report(rows=[first])
    dataset.documents["report-v2"] = make_document("report-v2", supersedes=["report-q1"])
    dataset.breach_reports["report-v2"] = make_report("report-v2", rows=[second])
    found = revisions(dataset)
    assert [(r.isin, r.field, r.before, r.after) for r in found] == [
        (ISIN_LISTED, "further_action", "Seeking instructions", "Waiver received")
    ]


def test_a_row_dropped_between_versions_is_a_revision(dataset):
    dataset.documents["report-v2"] = make_document("report-v2", supersedes=["report-q1"])
    dataset.breach_reports["report-v2"] = make_report("report-v2", nil_report=True, rows=[])
    assert [(r.field, r.before, r.after) for r in revisions(dataset)] == [("listed", "listed", "not listed")]


def test_identical_versions_show_no_revision(dataset):
    dataset.documents["report-v2"] = make_document("report-v2", supersedes=["report-q1"])
    dataset.breach_reports["report-v2"] = make_report("report-v2")
    assert revisions(dataset) == []


def _compare(dataset, statement):
    dataset.compliance_statements[statement.id] = statement
    return [c for c in compare_statements_with_reports(dataset) if c.statement == statement.id]


def test_an_issuer_statement_listing_the_breach_agrees_with_the_trustee(dataset):
    line = StatedException(isins=[ISIN_LISTED], page=1, covenant_as_reported="ratio", required_as_reported="<=5.00%")
    [result] = _compare(dataset, make_statement(breach=True, exceptions=[line]))
    assert (result.agreement, result.trustee_lists) == (Agreement.CONSISTENT, True)
    assert result.levels_only_in_statement == ()


def test_a_required_level_the_trustee_does_not_print_is_surfaced(dataset):
    line = StatedException(isins=[ISIN_LISTED], page=1, covenant_as_reported="ratio", required_as_reported="<=8%")
    [result] = _compare(dataset, make_statement(breach=True, exceptions=[line]))
    assert result.levels_only_in_statement == ("<=8%",)


def test_a_statement_of_compliance_differs_from_a_listing(dataset):
    [result] = _compare(dataset, make_statement(breach=False))
    assert result.agreement is Agreement.DIFFERS


def test_a_financial_only_statement_cannot_answer_a_listing_of_another_kind(dataset):
    row = make_row()
    item = row.items[0].model_copy(update={"category": CovenantCategory.AFFIRMATIVE})
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    [result] = _compare(dataset, make_statement(breach=False, scope=StatementScope.FINANCIAL_COVENANTS))
    assert result.agreement is Agreement.NOT_COMPARABLE


def test_a_breach_stated_by_the_issuer_but_absent_from_a_complete_report_differs(dataset):
    [result] = _compare(dataset, make_statement(breach=True, isin=ISIN_UNLISTED))
    assert (result.agreement, result.trustee_lists) == (Agreement.DIFFERS, False)


def test_without_a_complete_report_absence_is_not_compared(dataset):
    dataset.breach_reports["report-q1"] = make_report(extraction_complete=False, visually_reviewed=False)
    [result] = _compare(dataset, make_statement(breach=True, isin=ISIN_UNLISTED))
    assert (result.agreement, result.trustee_lists) == (Agreement.NOT_COMPARABLE, None)


def test_a_trustee_detection_after_the_statement_is_marked_as_possibly_derived(dataset):
    dataset.documents["report-q1"] = make_document(
        dates=[DocumentDate(kind=DocumentDateKind.DATED, value=date(2026, 8, 10), basis=DateBasis.STATED_IN_DOCUMENT)]
    )
    [result] = _compare(dataset, make_statement(breach=True))
    assert result.statement_dated == date(2026, 8, 10)
    assert result.trustee_detected == date(2026, 8, 14)
    assert result.trustee_could_rely_on_issuer
    assert not result.trustee_cites_certificate


def test_a_trustee_row_naming_the_certificate_is_recognised(dataset):
    row = make_row()
    item = row.items[0].model_copy(
        update={"covenant_as_reported": "basis the security cover certificate by the auditor"}
    )
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    [result] = _compare(dataset, make_statement(breach=True))
    assert result.trustee_cites_certificate
