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


def test_low_stock_at_threshold_boundary():
    assert compute_stock_status(5, 5) == STOCK_LOW


def test_low_stock_above_zero_below_threshold():
    assert compute_stock_status(1, 5) == STOCK_LOW


def test_in_stock_above_threshold():
    assert compute_stock_status(6, 5) == STOCK_IN_STOCK


def test_threshold_is_configurable():
    assert compute_stock_status(5, 3) == STOCK_IN_STOCK
    assert compute_stock_status(3, 3) == STOCK_LOW
    assert compute_stock_status(4, 3) == STOCK_IN_STOCK
