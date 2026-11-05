from datetime import date

import pytest

from brdo.consistency import (
    compare_notices_with_reports,
    compare_statements_with_reports,
    field_flows,
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


def test_each_party_is_credited_only_with_the_information_it_prints(dataset):
    line = StatedException(
        isins=[ISIN_LISTED],
        page=1,
        covenant_as_reported="ratio",
        required_as_reported="<=5%",
        actual_as_reported="7.00%",
    )
    dataset.compliance_statements["s"] = make_statement("s", breach=True, exceptions=[line])
    flows = {flow.field: (flow.issuer, flow.trustee) for flow in field_flows(dataset)}
    assert flows["required level"] == (True, True)
    assert flows["issuer's measured level"] == (True, False)
    assert flows["obligation wording"] == (False, True)


def test_a_measured_level_is_not_mistaken_for_a_clause_reference(dataset):
    """The rule once read the "1.02" in a printed ROA of "-1.02%" as a numbered clause."""
    row = make_row()
    item = row.items[0].model_copy(
        update={
            "covenant_as_reported": "Issuer has not complied with the prescribed Return on Assets ratio. "
            "Return on Assets maintained is '-1.02%'",
            "levels_stated": ["1%", "1.02%"],
            "clause_reference_as_reported": None,
        }
    )
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    line = StatedException(
        isins=[ISIN_LISTED], page=1, covenant_as_reported="Return on Assets 6.5", actual_as_reported="-1.02%"
    )
    dataset.compliance_statements["s"] = make_statement("s", breach=True, exceptions=[line])
    flows = {flow.field: flow for flow in field_flows(dataset)}
    assert (flows["clause reference"].issuer, flows["clause reference"].trustee) == (False, False)
    [measured] = flows["issuer's measured level"].trustee_evidence
    assert (measured.document, measured.locator, measured.matched) == ("report-q1", "row 1", "1.02%")


REFERENCES = [
    ("As per Clause 9.3 of the DTD", "Clause 9.3"),
    (
        "Clause no. 10.3 (a) (ii) (B), (iii) (B), (iv) and (viii) of the Debenture Trust Deed",
        "Clause no. 10.3 (a) (ii) (B)",
    ),
    ("10. Non compliance w.r.t. clause 1.4.1(vi) of Negative Covenants", "clause 1.4.1(vi)"),
    ("As per Schedule 3 Clause 2 of the Debenture Trust Deed", "Schedule 3"),
    ("As per Schedule VIII of the Debenture Trust Deed", "Schedule VIII"),
    ("Part B Schedule I", "Schedule I"),
    ("SCHEDULE 3 Clause 2", "SCHEDULE 3"),
    ("Schedule 4 Paragraph 2.1 of the Debenture Trust Deed (DTD)", "Schedule 4"),
    ("in terms of para 4 of the deed", "para 4"),
    ("Article II of the Deed", "Article II"),
    ("Clause 10.2A (a) (i) of the Debenture Trust Deed", "Clause 10.2A (a) (i)"),
    ("a breach of the covenant in clause (c) of the deed", "clause (c)"),
]
NOT_REFERENCES = [
    "Issuer has not complied with the prescribed Return on Assets ratio. Return on Assets maintained is '-1.02%'",
    "Return on Assets maintained is \u22121.02%",
    "-1.02% against a minimum of 1%",
    "1.5 month liabilities after including put options",
    "6.5% (Six Decimal Point Five Percent)",
    "a Write-Off Ratio may not at any time increase above 6.5%",
    "30.06.2026: DSCR below 1.2",
    "1.0 (one decimal zero) times the outstanding",
    "Net worth of Rs. 870 crores and 1.5 month liabilities",
    "the said clause of the deed",
    "as per the Debenture Trust Deed",
    "(e) a Write-Off Ratio may not at any time increase above 6.5%",
    "2.6 (ii) The Company shall at all times maintain",
    "as required under Section 186 of the Companies Act",
    "in breach of the Articles of Association",
    "Tier I Capital",
    "PAR 90+ (+) TTM Write Off",
    "Clasue 9.8 (ii), (iii) of the Debenture Trust Deed",
]


def _trustee_clause_flow(dataset, text: str, transcribed: str | None = None):
    row = make_row()
    item = row.items[0].model_copy(update={"covenant_as_reported": text, "clause_reference_as_reported": transcribed})
    dataset.breach_reports["report-q1"] = make_report(rows=[row.model_copy(update={"items": [item]})])
    dataset.compliance_statements["s"] = make_statement("s", breach=True, exceptions=[])
    return next(f for f in field_flows(dataset) if f.field == "clause reference")


@pytest.mark.parametrize(("text", "matched"), REFERENCES)
def test_named_and_numbered_references_count(dataset, text, matched):
    flow = _trustee_clause_flow(dataset, text)
    assert flow.trustee and [e.matched for e in flow.trustee_evidence] == [matched]


@pytest.mark.parametrize("text", NOT_REFERENCES)
def test_numbers_dates_headings_and_statutes_are_not_clause_references(dataset, text):
    assert not _trustee_clause_flow(dataset, text).trustee


def test_a_transcribed_clause_reference_counts_even_where_the_rule_would_miss_it(dataset):
    flow = _trustee_clause_flow(dataset, "2.6 (ii) The Company shall at all times maintain", transcribed="2.6")
    assert flow.trustee and [e.matched for e in flow.trustee_evidence] == ["2.6"]


def test_every_supporting_line_is_kept_and_what_was_examined_is_counted(dataset):
    lines = [
        StatedException(isins=[ISIN_LISTED], page=8, covenant_as_reported="PAR 30", required_as_reported="<=4%"),
        StatedException(isins=[ISIN_LISTED], page=8, covenant_as_reported="PAR 90", required_as_reported="<=3%"),
        StatedException(isins=[ISIN_LISTED], page=9, covenant_as_reported="Losses", required_as_reported="Profit"),
    ]
    dataset.compliance_statements["s"] = make_statement("s", breach=True, exceptions=lines)
    flow = next(f for f in field_flows(dataset) if f.field == "required level")
    assert flow.issuer_examined == 3
    assert [(e.locator, e.matched) for e in flow.issuer_evidence] == [
        ("exception line 1", "<=4%"),
        ("exception line 2", "<=3%"),
    ]
    deeds = next(f for f in field_flows(dataset) if f.field == "deed dates")
    assert (deeds.trustee, deeds.trustee_examined) == (False, 0)
