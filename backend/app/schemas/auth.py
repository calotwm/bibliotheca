"""Account-management schemas for the auth API."""

from pydantic import BaseModel, Field


class AccountUpdateRequest(BaseModel):
    """PATCH /api/auth/me body.

    ``current_password`` is always required. At least one of
    ``new_username`` / ``new_password`` must be provided. Passwords are NOT
    stripped so surrounding whitespace is preserved verbatim for hashing.
    """

    current_password: str = Field(min_length=1, max_length=255)
    new_username: str | None = Field(default=None, max_length=120)
    new_password: str | None = Field(default=None, min_length=6, max_length=255)


class AccountUpdateResponse(BaseModel):
    """Updated account info returned by PATCH /api/auth/me."""

    id: int
    username: str
    role: str