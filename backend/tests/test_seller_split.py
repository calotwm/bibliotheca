"""Unit tests for the automatic share split (``compute_shares``)."""

from decimal import Decimal

from app.services.seller_split import compute_shares


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
