"""A census is measured, not republished, so its count and sample must be reproducible from the file alone."""

from brdo.census import check_census, draw_sample, marked_not_received
from brdo.models import MonitoringCensus
from tests.conftest import ISIN_LISTED, ISIN_UNLISTED, QUARTER, SHA

OTHER = "INE00VD07016"
PAGES = [f"0001 Example {ISIN_LISTED} 10.00 Secured Yes", f"0002 Example {ISIN_UNLISTED} 5.00 Secured Yes {OTHER}"]


def _census(**values) -> MonitoringCensus:
    record = {"id": "census-q1", "document": "report-q1", "trustee": "trustee-a", "period": QUARTER}
    record |= {"isins_printed": 3, "sample": [ISIN_UNLISTED, OTHER]}
    return MonitoringCensus(**(record | values))


def test_the_sample_is_fixed_by_the_seed_and_not_by_input_order():
    population = [ISIN_LISTED, ISIN_UNLISTED, OTHER]
    first = draw_sample(population, [], 2, SHA)
    assert first == draw_sample(list(reversed(population)), [], 2, SHA)
    assert len(first) == 2 and first == sorted(first)


def test_listed_isins_never_enter_the_sample():
    assert ISIN_LISTED not in draw_sample([ISIN_LISTED, ISIN_UNLISTED, OTHER], [ISIN_LISTED], 3, SHA)


def test_a_census_that_matches_its_file_has_no_problems(dataset):
    assert check_census(dataset, _census(), PAGES) == []


def test_a_wrong_count_or_sample_is_caught(dataset):
    problems = check_census(dataset, _census(isins_printed=4, sample=[OTHER]), PAGES)
    assert any("prints 3 valid ISINs" in p for p in problems)
    assert any("sample drawn from the file" in p for p in problems)


def test_a_listed_isin_missing_from_the_census_must_be_recorded(dataset):
    pages = [f"0002 Example {ISIN_UNLISTED} 5.00 Secured Yes {OTHER}"]
    problems = check_census(dataset, _census(isins_printed=2), pages)
    assert any("listed ISINs the file omits" in p for p in problems)
    assert check_census(dataset, _census(isins_printed=2, listed_not_printed=[ISIN_LISTED]), pages) == []


def test_a_row_marking_the_report_not_received_is_read_and_must_be_recorded(dataset):
    pages = [f"0001 Example {ISIN_LISTED} 10.00 Secured Yes", f"0002 Example {OTHER} 5.00 UnSecured No Not Received"]
    assert marked_not_received(pages) == {OTHER}
    record = _census(isins_printed=2, sample=[OTHER])
    assert any("not received" in p for p in check_census(dataset, record, pages))
    assert check_census(dataset, _census(isins_printed=2, sample=[OTHER], report_not_received=[OTHER]), pages) == []
