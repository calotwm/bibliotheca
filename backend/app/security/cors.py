"""CORS allowlist parsing and validation."""

from __future__ import annotations


def parse_allowed_origins(raw: str) -> list[str]:
    """Parse a comma-separated allowlist, rejecting empty and wildcard values.

    ``"*"`` is incompatible with ``allow_credentials=True``: a wildcard would
    silently grant credentialed requests to any origin, so we fail instead of
    permitting it.
    """
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        raise ValueError("ALLOWED_ORIGINS must not be empty")
    if "*" in origins:
        raise ValueError(
            "ALLOWED_ORIGINS must not contain '*' — wildcard is incompatible "
            "with allow_credentials=True"
        )
    return origins
