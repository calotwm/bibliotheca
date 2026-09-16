"""Unit tests for the automatic share split (``compute_shares``) and the
shared ``seller_bucket`` classification helper."""

from decimal import Decimal

import pytest

from app.services.seller_split import compute_shares, seller_bucket


def _pair(juli: str, cande: str) -> tuple[Decimal, Decimal]:
    return Decimal(juli), Decimal(cande)


def test_none_observaciones_defaults_juli_85_15():
    assert compute_shares(None) == _pair("85", "15")


def test_blank_observaciones_defaults_juli_85_15():
    assert compute_shares("") == _pair("85", "15")
    assert compute_shares("   ") == _pair("85", "15")


def test_juli_only_is_85_15():
    assert compute_shares("Juli") == _pair("85", "15")


def test_cande_only_is_0_100():
    assert compute_shares("Cande") == _pair("0", "100")


def test_both_names_is_50_50():
    assert compute_shares("Juli y Cande") == _pair("50", "50")


def test_both_names_reversed_is_50_50():
    assert compute_shares("Cande y Juli") == _pair("50", "50")


def test_both_names_embedded_is_50_50():
    assert compute_shares("Consignación Juli y Cande") == _pair("50", "50")


def test_no_names_defaults_juli_85_15():
    assert compute_shares("En consignación 30%") == _pair("85", "15")


def test_juli_mention_without_cande_is_85_15():
    assert compute_shares("1 Juli 1 de las dos") == _pair("85", "15")


def test_case_insensitive_matching():
    assert compute_shares("CANDE") == _pair("0", "100")
    assert compute_shares("juli y cande") == _pair("50", "50")


# --- seller_bucket: pure-Python classification helper -----------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        ("Juli", "Juli"),
        ("Cande", "Cande"),
        ("Juli y Cande", "Juli y Cande"),
        ("Cande y Juli", "Juli y Cande"),
        ("", "Juli"),
        (None, "Juli"),
        ("En consignación 30%", "Juli"),
    ],
)
def test_seller_bucket_returns_correct_bucket(value, expected):
    assert seller_bucket(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "Juli",
        "Cande",
        "Juli y Cande",
        "Cande y Juli",
        "",
        None,
        "En consignación 30%",
    ],
)
def test_seller_bucket_agrees_with_compute_shares(value):
    """The bucket helper and compute_shares MUST agree so the filter and the
    earnings split can never drift."""
    expected_shares = compute_shares(value)
    bucket = seller_bucket(value)
    if bucket == "Juli y Cande":
        assert expected_shares == _pair("50", "50")
    elif bucket == "Cande":
        assert expected_shares == _pair("0", "100")
    else:  # "Juli"
        assert expected_shares == _pair("85", "15")
