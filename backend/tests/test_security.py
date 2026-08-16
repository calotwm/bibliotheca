"""Unit tests for security primitives: JWT, password, CORS, role deps."""

import pytest
from fastapi import HTTPException
from jose import JWTError

from app.models import User
from app.security.cors import parse_allowed_origins
from app.security.deps import require_admin
from app.security.jwt import create_access_token, decode_token
from app.security.password import hash_password, verify_password


def test_password_hash_and_verify():
    hashed = hash_password("s3cret")
    assert hashed != "s3cret"
    assert verify_password("s3cret", hashed)
    assert not verify_password("wrong", hashed)


def test_password_verify_invalid_hash():
    assert not verify_password("x", "not-a-valid-bcrypt-hash")


def test_jwt_roundtrip():
    token = create_access_token("admin", "admin")
    payload = decode_token(token)
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_jwt_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_parse_allowed_origins():
    assert parse_allowed_origins("http://a.com, https://b.com") == [
        "http://a.com",
        "https://b.com",
    ]


def test_parse_allowed_origins_rejects_empty():
    with pytest.raises(ValueError):
        parse_allowed_origins("")


def test_parse_allowed_origins_rejects_wildcard():
    with pytest.raises(ValueError):
        parse_allowed_origins("*")


async def test_require_admin_rejects_cashier():
    cashier = User(username="cashier", password_hash="x", role="cashier")
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(cashier)
    assert exc_info.value.status_code == 403


async def test_require_admin_allows_admin():
    admin = User(username="admin", password_hash="x", role="admin")
    result = await require_admin(admin)
    assert result is admin
