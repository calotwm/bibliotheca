"""Tests for environment configuration."""

import pytest
from pydantic import ValidationError

from app.config import Settings

REQUIRED_VARS = ("SECRET_KEY", "ALLOWED_ORIGINS", "ADMIN_USERNAME", "ADMIN_PASSWORD")


@pytest.fixture
def clear_required_env(monkeypatch):
    for var in REQUIRED_VARS:
        monkeypatch.delenv(var, raising=False)
    # BUSINESS_* defaults are asserted as empty; the test-suite env (conftest)
    # sets them, so clear them too to exercise the true defaults.
    for var in ("BUSINESS_NAME", "BUSINESS_CUIT", "BUSINESS_ADDRESS", "BUSINESS_CONDITION"):
        monkeypatch.delenv(var, raising=False)


def _settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_missing_required_vars_raise(clear_required_env):
    with pytest.raises(ValidationError):
        _settings()


def test_required_vars_must_be_non_empty(clear_required_env):
    with pytest.raises(ValidationError):
        _settings(
            SECRET_KEY="   ",
            ALLOWED_ORIGINS="http://localhost:5173",
            ADMIN_USERNAME="admin",
            ADMIN_PASSWORD="admin",
        )


def test_defaults_apply(clear_required_env):
    s = _settings(
        SECRET_KEY="secret",
        ALLOWED_ORIGINS="http://localhost:5173",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="admin",
    )
    assert s.database_url == "sqlite+aiosqlite:///./bibliotheca.db"
    assert s.low_stock_threshold == 5
    assert s.rate_limit_login == "5/minute"
    assert s.rate_limit_api == "60/minute"
    assert s.access_token_expire_minutes == 60
    assert s.business_name == ""
    assert s.business_cuit == ""
    assert s.business_address == ""
    assert s.business_condition == ""


def test_allowed_origins_rejects_wildcard(clear_required_env):
    with pytest.raises(ValidationError):
        _settings(
            SECRET_KEY="secret",
            ALLOWED_ORIGINS="*",
            ADMIN_USERNAME="admin",
            ADMIN_PASSWORD="admin",
        )


def test_allowed_origins_parsing(clear_required_env):
    s = _settings(
        SECRET_KEY="secret",
        ALLOWED_ORIGINS="http://localhost:5173, https://app.example.com",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="admin",
    )
    assert s.allowed_origins_list == [
        "http://localhost:5173",
        "https://app.example.com",
    ]


def test_env_overrides_apply(clear_required_env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "from-env")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://env.example.com")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin")
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", "3")
    s = Settings(_env_file=None)
    assert s.secret_key == "from-env"
    assert s.allowed_origins_list == ["http://env.example.com"]
    assert s.low_stock_threshold == 3
