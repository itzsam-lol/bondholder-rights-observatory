import pytest

from brdo.identifiers import is_valid_cin, is_valid_isin, is_valid_lei, isin_issuer_code, printed_isins


@pytest.mark.parametrize("isin", ["INE501X07588", "INE0INX07015", "INE906B07HP8", "INE01W207017", "US0378331005"])
def test_real_isins_pass_the_check_digit(isin):
    assert is_valid_isin(isin)


@pytest.mark.parametrize(
    "isin",
    ["INE501X07589", "INE501X0758", "ine501x07588", "INE501X075888", "", "INE501X0758A"],
)
def test_malformed_or_mistyped_isins_fail(isin):
    assert not is_valid_isin(isin)


def test_a_transposition_is_caught_by_the_check_digit():
    assert not is_valid_isin("INE501X07858")


def test_issuer_code_is_the_four_characters_after_the_issuer_type():
    assert isin_issuer_code("INE501X07588") == "501X"
    assert isin_issuer_code("INE0N5S07052") == "0N5S"


def test_issuer_code_refuses_foreign_isins():
    with pytest.raises(ValueError):
        isin_issuer_code("US0378331005")


def test_cin_accepts_private_and_public_company_forms():
    assert is_valid_cin("U65921DL1993PTC283660")
    assert is_valid_cin("U65921DL1993PLC283660")
    assert not is_valid_cin("U65921DL1993PTC28366")


def test_lei_check_digits():
    assert is_valid_lei("335800Q6CHM9LTEPY552")
    assert not is_valid_lei("335800Q6CHM9LTEPY553")


def test_printed_isins_keeps_only_identifiers_that_pass_the_check_digit():
    text = "0995 Infinity INE00VD07016 147.00 Secured, then a misprint INE296A07RDI and INE501X07588."
    assert printed_isins(text) == {"INE00VD07016", "INE501X07588"}
