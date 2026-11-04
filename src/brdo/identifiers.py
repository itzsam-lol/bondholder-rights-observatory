"""Validation of the public identifiers used to key records."""

import re

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_CIN_RE = re.compile(r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$")
_LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


def _luhn_valid(digits: str) -> bool:
    total = 0
    for position, char in enumerate(reversed(digits)):
        value = int(char)
        if position % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def is_valid_isin(value: str) -> bool:
    """Check ISIN format and its ISO 6166 check digit."""
    if not _ISIN_RE.match(value):
        return False
    expanded = "".join(str(int(char, 36)) for char in value)
    return _luhn_valid(expanded)


def isin_issuer_code(isin: str) -> str:
    """Return the issuer segment of an Indian ISIN (``INE501X07588`` -> ``501X``).

    Indian ISINs are structured as country code, issuer type, a four-character
    issuer code, security type, serial number and check digit. ISINs that share
    an issuer code were allotted to the same issuer.
    """
    if not isin.startswith("IN") or not is_valid_isin(isin):
        raise ValueError(f"not a valid Indian ISIN: {isin}")
    return isin[3:7]


def is_valid_cin(value: str) -> bool:
    """Corporate Identity Number issued by India's Ministry of Corporate Affairs."""
    return bool(_CIN_RE.match(value))


def is_valid_lei(value: str) -> bool:
    """ISO 17442 Legal Entity Identifier, including its ISO 7064 check digits."""
    if not _LEI_RE.match(value):
        return False
    return int("".join(str(int(char, 36)) for char in value)) % 97 == 1


_ISIN_TOKEN = re.compile(r"\bIN[A-Z0-9]{10}\b")


def printed_isins(text: str) -> frozenset[str]:
    """Indian ISINs printed in ``text`` that pass the check digit."""
    return frozenset(token for token in _ISIN_TOKEN.findall(text) if is_valid_isin(token))
