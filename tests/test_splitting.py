from decimal import Decimal

import pytest

from app.services.splitting import (
    SplitError,
    compute_shares,
    split_equal,
    split_percentage,
    split_unequal,
)


def test_split_equal_divides_evenly():
    shares = split_equal(Decimal("90.00"), [1, 2, 3])
    assert shares == {1: Decimal("30.00"), 2: Decimal("30.00"), 3: Decimal("30.00")}


def test_split_equal_distributes_remainder_cents():
    shares = split_equal(Decimal("10.00"), [1, 2, 3])
    assert sum(shares.values()) == Decimal("10.00")
    # 10.00 / 3 = 3.33 each with 1 cent left over, given to the lowest user_id
    assert shares[1] == Decimal("3.34")
    assert shares[2] == Decimal("3.33")
    assert shares[3] == Decimal("3.33")


def test_split_equal_rejects_duplicate_participants():
    with pytest.raises(SplitError):
        split_equal(Decimal("10.00"), [1, 1, 2])


def test_split_equal_rejects_empty_participants():
    with pytest.raises(SplitError):
        split_equal(Decimal("10.00"), [])


def test_split_unequal_accepts_matching_total():
    shares = split_unequal(Decimal("100.00"), {1: Decimal("60.00"), 2: Decimal("40.00")})
    assert shares == {1: Decimal("60.00"), 2: Decimal("40.00")}


def test_split_unequal_rejects_mismatched_total():
    with pytest.raises(SplitError):
        split_unequal(Decimal("100.00"), {1: Decimal("60.00"), 2: Decimal("30.00")})


def test_split_percentage_computes_amounts():
    shares = split_percentage(Decimal("200.00"), {1: Decimal("50"), 2: Decimal("50")})
    assert shares == {1: Decimal("100.00"), 2: Decimal("100.00")}


def test_split_percentage_handles_rounding_remainder():
    shares = split_percentage(Decimal("100.00"), {1: Decimal("33.33"), 2: Decimal("33.33"), 3: Decimal("33.34")})
    assert sum(shares.values()) == Decimal("100.00")


def test_split_percentage_rejects_totals_other_than_100():
    with pytest.raises(SplitError):
        split_percentage(Decimal("100.00"), {1: Decimal("50"), 2: Decimal("40")})


def test_compute_shares_equal():
    amounts, percentages = compute_shares("equal", Decimal("30.00"), {1: None, 2: None})
    assert amounts == {1: Decimal("15.00"), 2: Decimal("15.00")}
    assert percentages is None


def test_compute_shares_unequal():
    amounts, percentages = compute_shares(
        "unequal", Decimal("30.00"), {1: Decimal("10.00"), 2: Decimal("20.00")}
    )
    assert amounts == {1: Decimal("10.00"), 2: Decimal("20.00")}
    assert percentages is None


def test_compute_shares_percentage():
    amounts, percentages = compute_shares(
        "percentage", Decimal("30.00"), {1: Decimal("50"), 2: Decimal("50")}
    )
    assert amounts == {1: Decimal("15.00"), 2: Decimal("15.00")}
    assert percentages == {1: Decimal("50"), 2: Decimal("50")}


def test_compute_shares_unknown_split_type():
    with pytest.raises(SplitError):
        compute_shares("bogus", Decimal("30.00"), {1: None})
