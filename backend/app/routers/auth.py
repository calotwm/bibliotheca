"""Auth endpoints: login and current-user.

NOTE: no ``from __future__ import annotations`` here — slowapi's ``limit``
decorator wraps the endpoint and resolves annotations against the wrapper's
module globals, so string annotations would break request-body parsing.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import User
from ..security.deps import require_user
from ..security.jwt import create_access_token
from ..security.limiter import limiter
from ..security.password import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

_settings = get_settings()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str


class UserResponse(BaseModel):
    username: str
    role: str


@router.post("/login", response_model=LoginResponse)
@limiter.limit(_settings.rate_limit_login)
async def login(
    request: Request,
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )

    token = create_access_token(user.username, user.role)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
@limiter.limit(_settings.rate_limit_api)
async def me(
    request: Request,
    user: Annotated[User, Depends(require_user)],
) -> UserResponse:
    return UserResponse(username=user.username, role=user.role)
