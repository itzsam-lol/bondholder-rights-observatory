"""Published follow-up states stay distinct: a late filing made good is not a financial covenant restored."""

from datetime import date

from brdo.consistency import follow_up_states
from brdo.models import BreachNotice, ReportedAction
from brdo.vocab import ActionKind, CovenantCategory
from tests.conftest import ISIN_LISTED, QUARTER, make_report, make_row


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
    assert state.basis == "report-q1 row 1: cure_reported, covenant category financial"


def _letter(identifier: str, period_end: date | None, **fields) -> BreachNotice:
    return BreachNotice(
        id=identifier,
        document="report-q1",
        page=1,
        trustee="trustee-a",
        isins=[ISIN_LISTED],
        issued_on=date(2026, 9, 1),
        period_end=period_end,
        **fields,
    )


def test_a_letter_about_another_quarter_is_not_follow_up_of_this_one(dataset):
    dataset.breach_notices["march"] = _letter("march", date(2026, 3, 31), meeting_proposed_for=date(2026, 7, 3))
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == set()
    dataset.breach_notices["june"] = _letter("june", QUARTER.end, meeting_proposed_for=date(2026, 9, 10))
    dataset.breach_notices["continued"] = _letter("continued", None, adjourned_for_lack_of_quorum=True)
    assert _states(dataset)[("trustee-a", ISIN_LISTED)] == {
        "meeting reported as scheduled",
        "meeting adjourned for lack of quorum",
    }
