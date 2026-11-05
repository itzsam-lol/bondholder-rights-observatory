"""Published follow-up states stay distinct: a late filing made good is not a financial covenant restored."""

from datetime import date

from brdo.consistency import PeriodAttribution, follow_up_states, link_continuations, unattributed_follow_up
from brdo.models import BreachNotice, ReportedAction
from brdo.vocab import ActionKind, CovenantCategory, NoticeKind
from tests.conftest import ISIN_LISTED, ISIN_UNLISTED, QUARTER, make_report, make_row


def _cured(category: CovenantCategory):
    row = make_row()
    item = row.items[0].model_copy(update={"category": category})
    return row.model_copy(update={"items": [item], "actions": [ReportedAction(kind=ActionKind.CURE_REPORTED)]})


def _states(dataset) -> dict[tuple[str, str], set[str]]:
    published, listed = follow_up_states(dataset, QUARTER.end)
    found = {key: set() for key in listed}
    for state in published:
        found[(state.trustee, state.isin)].add(state.state)
    return found


def test_a_cure_is_typed_by_the_covenant_it_concerns(dataset):
    dataset.breach_reports["report-q1"] = make_report(rows=[_cured(CovenantCategory.AFFIRMATIVE)])
    [states] = _states(dataset).values()
    assert states == {"cure reported for another obligation, such as a late filing"}
    dataset.breach_reports["report-q1"] = make_report(rows=[_cured(CovenantCategory.FINANCIAL)])
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == {"cure reported for a financial covenant"}


def test_a_listing_with_no_follow_up_is_kept_with_no_state(dataset):
    assert _states(dataset) == {("trustee-a", ISIN_LISTED): set()}


def test_every_state_says_where_the_record_shows_it(dataset):
    dataset.breach_reports["report-q1"] = make_report(rows=[_cured(CovenantCategory.FINANCIAL)])
    [state] = follow_up_states(dataset, QUARTER.end)[0]
    assert state.basis == "report-q1 row 1: cure_reported, covenant categories financial"


def _letter(identifier: str, period_end: date | None, issued_on: date = date(2026, 9, 1), **fields) -> BreachNotice:
    return BreachNotice(
        id=identifier,
        document="report-q1",
        page=1,
        trustee="trustee-a",
        isins=[ISIN_LISTED],
        issued_on=issued_on,
        period_end=period_end,
        **fields,
    )


def test_a_letter_about_another_quarter_is_not_follow_up_of_this_one(dataset):
    dataset.breach_notices["march"] = _letter("march", date(2026, 3, 31), meeting_proposed_for=date(2026, 7, 3))
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == set()
    dataset.breach_notices["june"] = _letter("june", QUARTER.end, meeting_proposed_for=date(2026, 9, 10))
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == {"meeting reported as scheduled"}


def test_a_breach_letter_with_no_quarter_is_not_counted_for_every_quarter(dataset):
    dataset.breach_notices["undated"] = _letter("undated", None, meeting_proposed_for=date(2026, 9, 10))
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == set()


# --- Cures are typed only where every covenant the row lists for the ISIN is of one kind ---


def _cured_items(*categories: CovenantCategory, isins_per_item=None):
    row = make_row()
    items = [
        row.items[0].model_copy(
            update={"category": category, "isins": (isins_per_item or {}).get(index, [ISIN_LISTED])}
        )
        for index, category in enumerate(categories)
    ]
    return row.model_copy(update={"items": items, "actions": [ReportedAction(kind=ActionKind.CURE_REPORTED)]})


def test_a_cure_in_a_mixed_row_is_not_typed_as_financial(dataset):
    dataset.breach_reports["report-q1"] = make_report(
        rows=[_cured_items(CovenantCategory.FINANCIAL, CovenantCategory.OTHER)]
    )
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == {"cure reported, for covenants of more than one kind"}


def test_a_cure_of_a_row_of_financial_covenants_only_is_financial(dataset):
    dataset.breach_reports["report-q1"] = make_report(
        rows=[_cured_items(CovenantCategory.FINANCIAL, CovenantCategory.FINANCIAL)]
    )
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == {"cure reported for a financial covenant"}


def test_a_cure_is_typed_by_the_items_printed_beside_each_isin(dataset):
    """A row may print a financial covenant beside one ISIN and a filing obligation beside another."""
    row = _cured_items(
        CovenantCategory.FINANCIAL, CovenantCategory.OTHER, isins_per_item={0: [ISIN_LISTED], 1: [ISIN_UNLISTED]}
    )
    dataset.breach_reports["report-q1"] = make_report(rows=[row])
    states = _states(dataset)
    assert states[("trustee-a", ISIN_LISTED)] == {"cure reported for a financial covenant"}
    assert states[("trustee-a", ISIN_UNLISTED)] == {"cure reported for another obligation, such as a late filing"}


# --- A letter naming no quarter counts only where a rule ties it to one ---


def _continuation(identifier: str, issued_on: date, **fields) -> BreachNotice:
    kind = NoticeKind.MEETING_CONTINUATION
    return _letter(identifier, None, issued_on, kind=kind, adjourned_for_lack_of_quorum=True, **fields)


def test_a_continuation_counts_for_the_quarter_of_the_earlier_letter_in_its_file(dataset):
    dataset.breach_notices["first"] = _letter("first", QUARTER.end, meeting_proposed_for=date(2026, 8, 20))
    dataset.breach_notices["again"] = _continuation("again", date(2026, 9, 1))
    published, _ = follow_up_states(dataset, QUARTER.end)
    adjourned = [s for s in published if s.state == "meeting adjourned for lack of quorum"]
    assert [(s.attribution, s.period_end) for s in adjourned] == [(PeriodAttribution.LINKED_BY_RULE, QUARTER.end)]
    assert "continues first" in adjourned[0].basis and not unattributed_follow_up(dataset)


def test_a_continuation_with_no_earlier_letter_counts_for_no_quarter(dataset):
    dataset.breach_notices["again"] = _continuation("again", date(2026, 9, 1))
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == set()
    [state] = [s for s in unattributed_follow_up(dataset) if s.state == "meeting adjourned for lack of quorum"]
    assert (state.period_end, state.attribution) == (None, PeriodAttribution.NOT_ATTRIBUTABLE)


def test_a_continuation_is_not_tied_to_a_letter_whose_meeting_came_after_it(dataset):
    dataset.breach_notices["first"] = _letter("first", QUARTER.end, meeting_proposed_for=date(2026, 9, 20))
    dataset.breach_notices["again"] = _continuation("again", date(2026, 9, 1))
    assert link_continuations(dataset)[("again", ISIN_LISTED)].period_end is None


def test_a_continuation_with_earlier_letters_of_different_quarters_is_not_tied(dataset):
    dataset.breach_notices["march"] = _letter("march", date(2026, 3, 31), meeting_proposed_for=date(2026, 5, 20))
    dataset.breach_notices["june"] = _letter("june", QUARTER.end, meeting_proposed_for=date(2026, 8, 20))
    dataset.breach_notices["again"] = _continuation("again", date(2026, 9, 1))
    link = link_continuations(dataset)[("again", ISIN_LISTED)]
    assert link.period_end is None and link.continues == ("june", "march")
