"""Parsing of dates as printed in Indian regulatory disclosures.

Disclosures print dates in many shapes ("22-07-26", "30-Jun-26",
"30th September, 2023", "14.08.2026"). Records keep the printed text and the
parsed value side by side; this module provides the single parser used both to
draft records and to check that a recorded value agrees with its printed text.
Indian disclosures write day before month, so numeric dates are read that way.
"""

import re
from datetime import date

_MONTHS = {
    name: index
    for index, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for name in names
}

_NUMERIC = re.compile(r"^(\d{1,2})[-./](\d{1,2})[-./](\d{2}|\d{4})$")
_DAY_MONTHNAME_YEAR = re.compile(r"^(\d{1,2})(?:st|nd|rd|th)?[-\s]+([a-z]+)[-,\s]+(\d{2}|\d{4})$")
_MONTHNAME_DAY_YEAR = re.compile(r"^([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$")


def _year(text: str) -> int:
    value = int(text)
    return 2000 + value if len(text) == 2 else value


def _build(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_printed_date(raw: str) -> date | None:
    """Parse a printed date, or return ``None`` if the text is not exactly one date."""
    text = " ".join(raw.strip().lower().split())
    if match := _NUMERIC.match(text):
        day, month, year = match.groups()
        return _build(_year(year), int(month), int(day))
    if match := _DAY_MONTHNAME_YEAR.match(text):
        day, month_name, year = match.groups()
        month = _MONTHS.get(month_name)
        return _build(_year(year), month, int(day)) if month else None
    if match := _MONTHNAME_DAY_YEAR.match(text):
        month_name, day, year = match.groups()
        month = _MONTHS.get(month_name)
        return _build(int(year), month, int(day)) if month else None
    return None


_MONTH_NAMES = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ANY_DATE = re.compile(
    rf"\b(\d{{1,2}})\s?(?:st|nd|rd|th)?[-\s]*({_MONTH_NAMES})[a-z]*[-,\s]*(\d\s?\d\s?\d\s?\d|\d{{2}})\b"
    rf"|\b({_MONTH_NAMES})[a-z]*\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b"
    r"|\b(\d{1,2})[-./](\d{1,2})[-./ ]\s?(\d{4}|\d{2})\b"
)


def find_printed_dates(text: str) -> set[date]:
    """Every date printed in a passage, tolerating the broken spacing PDF extraction leaves behind."""
    found: set[date] = set()
    for match in _ANY_DATE.finditer(" ".join(text.lower().split())):
        day_a, month_a, year_a, month_b, day_b, year_b, day_c, month_c, year_c = match.groups()
        if day_a:
            parsed = _build(_year(year_a.replace(" ", "")), _MONTHS[month_a], int(day_a))
        elif month_b:
            parsed = _build(int(year_b), _MONTHS[month_b], int(day_b))
        else:
            parsed = _build(_year(year_c), int(month_c), int(day_c))
        if parsed:
            found.add(parsed)
    return found
