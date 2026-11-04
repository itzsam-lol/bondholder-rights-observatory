"""Published follow-up states stay distinct: a late filing made good is not a financial covenant restored."""

from brdo.models import ReportedAction
from brdo.report import _closure_states
from brdo.vocab import ActionKind, CovenantCategory
from tests.conftest import ISIN_LISTED, QUARTER, make_report, make_row


def _cured(category: CovenantCategory):
    row = make_row()
    item = row.items[0].model_copy(update={"category": category})
    return row.model_copy(update={"items": [item], "actions": [ReportedAction(kind=ActionKind.CURE_REPORTED)]})


def test_a_cure_is_typed_by_the_covenant_it_concerns(dataset):
    dataset.breach_reports["report-q1"] = make_report(rows=[_cured(CovenantCategory.AFFIRMATIVE)])
    [states] = _closure_states(dataset, QUARTER.end).values()
    assert states == {"cure reported for another obligation, such as a late filing"}
    dataset.breach_reports["report-q1"] = make_report(rows=[_cured(CovenantCategory.FINANCIAL)])
    assert _closure_states(dataset, QUARTER.end)[("trustee-a", ISIN_LISTED)] == {
        "cure reported for a financial covenant"
    }


def test_a_listing_with_no_follow_up_is_kept_with_no_state(dataset):
    assert _closure_states(dataset, QUARTER.end) == {("trustee-a", ISIN_LISTED): set()}
