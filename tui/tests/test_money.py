"""Coin expression parser tests."""

import pytest

from tui.money import fmt_cp, is_transaction, money_to_cp, split_cp


def test_single_amounts():
    assert money_to_cp("2gp") == 200
    assert money_to_cp("5 sp") == 50
    assert money_to_cp("1pp") == 1000
    assert money_to_cp("1ep") == 50
    assert money_to_cp("7cp") == 7
    assert money_to_cp("7") == 7            # bare number = copper
    assert money_to_cp("2GP") == 200        # case-insensitive


def test_juxtaposition_adds():
    assert money_to_cp("2gp 5sp") == 250
    assert money_to_cp("2gp5sp") == 250          # no space needed
    assert money_to_cp("1pp 2gp 3sp 4cp") == 1234


def test_signed_and_arithmetic():
    assert money_to_cp("+2gp 5sp") == 250
    assert money_to_cp("-1gp") == -100
    assert money_to_cp("2gp - 5sp") == 150
    assert money_to_cp("3gp + 12sp") == 420
    assert money_to_cp("(3gp + 12sp) / 4") == 105
    assert money_to_cp("120gp / 4") == 3000
    assert money_to_cp("3 * 5gp") == 1500


def test_errors():
    for bad in ("", "  ", "2zp", "gold", "2gp +", "import os", "2**8",
                "1gp / 0"):
        with pytest.raises(ValueError):
            money_to_cp(bad)


def test_split_and_format():
    assert split_cp(1234) == (12, 3, 4)
    assert fmt_cp(1234) == "12 GP 3 SP 4 CP"
    assert fmt_cp(200) == "2 GP"
    assert fmt_cp(0) == "0 CP"
    assert fmt_cp(-150) == "-1 GP 5 SP"
    assert fmt_cp(105.5) == "1 GP 5 CP (+0.50 cp)"


def test_is_transaction():
    assert is_transaction("+2gp")
    assert is_transaction("  -5sp")
    assert not is_transaction("2gp + 5sp")


def test_transaction_sign_covers_whole_amount():
    from tui.money import transaction_cp
    assert transaction_cp("-2gp 5sp") == -250
    assert transaction_cp("-2gp5sp") == -250
    assert transaction_cp("+2gp 5sp") == 250
    assert transaction_cp("-(3gp)/3") == -100
    with pytest.raises(ValueError):
        transaction_cp("2gp")               # no sign = not a transaction
