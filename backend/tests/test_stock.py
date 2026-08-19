"""Unit tests for the stock status (badge) computation."""

from app.services.stock import (
    STOCK_IN_STOCK,
    STOCK_LOW,
    STOCK_OUT,
    compute_stock_status,
)


def test_out_of_stock_at_zero():
    assert compute_stock_status(0, 5) == STOCK_OUT


def test_out_of_stock_when_negative():
    assert compute_stock_status(-3, 5) == STOCK_OUT


def test_in_stock_at_one():
    assert compute_stock_status(1, 5) == STOCK_IN_STOCK


def test_in_stock_above_threshold():
    assert compute_stock_status(6, 5) == STOCK_IN_STOCK


def test_low_tier_never_emitted():
    # With the binary model, a stock level at or below the old threshold is
    # still In Stock; the low-stock tier is never returned.
    assert compute_stock_status(1, 5) == STOCK_IN_STOCK
    assert compute_stock_status(3, 5) == STOCK_IN_STOCK
    assert compute_stock_status(5, 5) == STOCK_IN_STOCK


def test_threshold_is_ignored():
    # The threshold no longer influences the result (deprecated parameter).
    assert compute_stock_status(1, 1) == STOCK_IN_STOCK
    assert compute_stock_status(1, 0) == STOCK_IN_STOCK
    assert compute_stock_status(0, 100) == STOCK_OUT


def test_low_constant_still_exported_for_compat():
    assert STOCK_LOW == "Low"
