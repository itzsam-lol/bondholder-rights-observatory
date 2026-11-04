from datetime import date

import pytest

from brdo.dates import find_printed_dates, parse_printed_date


@pytest.mark.parametrize(
    "printed, expected",
    [
        ("22-07-26", date(2026, 7, 22)),
        ("5-01-2026", date(2026, 1, 5)),
        ("14.08.2026", date(2026, 8, 14)),
        ("30-Jun-26", date(2026, 6, 30)),
        ("12-Sep-2026", date(2026, 9, 12)),
        ("11th October 2023", date(2023, 10, 11)),
        ("30th September, 2023", date(2023, 9, 30)),
        ("September 16, 2026", date(2026, 9, 16)),
        ("  7  Sept  2025 ", date(2025, 9, 7)),
    ],
)
def test_printed_forms_seen_in_disclosures(printed, expected):
    assert parse_printed_date(printed) == expected


def test_numeric_dates_are_day_first():
    assert parse_printed_date("03-04-2026") == date(2026, 4, 3)


@pytest.mark.parametrize(
    "printed",
    [
        "30th September, 2023 till date",
        "13-08-2026 [Q1 FY 26-27]",
        "20th July 2024 and 20th October 2024",
        "NA",
        "",
        "31-02-2026",
    ],
)
def test_anything_but_exactly_one_valid_date_is_not_parsed(printed):
    assert parse_printed_date(printed) is None


@pytest.mark.parametrize(
    "passage, expected",
    [
        ("Trust Deed dated 16 th May, 2024 and 14 th July, 2025 respectively", {date(2024, 5, 16), date(2025, 7, 14)}),
        ("dated 26th September, 202 4", {date(2024, 9, 26)}),
        (
            "Agreement dated 31.10.2007, 14.08.2008 & 19.07.2007",
            {date(2007, 10, 31), date(2008, 8, 14), date(2007, 7, 19)},
        ),
        ("CRAs & SEBI - 27-Jul-26 DHs - 28-Jul-26", {date(2026, 7, 27), date(2026, 7, 28)}),
        ("deed dated December 20, 2016", {date(2016, 12, 20)}),
        ("email dt.14-08-2026 and Stock", {date(2026, 8, 14)}),
        ("sent via email dated 06-06 2025", {date(2025, 6, 6)}),
        ("no date in this passage, only 5% and Rs. 870 crores", set()),
    ],
)
def test_every_date_in_a_passage_is_found(passage, expected):
    assert find_printed_dates(passage) == expected
