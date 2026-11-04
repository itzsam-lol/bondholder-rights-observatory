from datetime import date

from brdo.consistency import compare_notices_with_reports, revisions, stated_thresholds
from brdo.models import BreachNotice
from tests.conftest import ISIN_LISTED, QUARTER, make_document, make_report, make_row


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
