"""Auth endpoints: login and current-user.

NOTE: no ``from __future__ import annotations`` here — slowapi's ``limit``
decorator wraps the endpoint and resolves annotations against the wrapper's
module globals, so string annotations would break request-body parsing.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import User
from ..schemas.auth import AccountUpdateRequest, AccountUpdateResponse
from ..security.deps import require_user
from ..security.jwt import create_access_token
from ..security.limiter import limiter
from ..security.password import hash_password, verify_password
from ..services.audit import log_audit

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


async def _username_taken(
    session: AsyncSession, username: str, *, exclude_id: int
) -> bool:
    query = select(User.id).where(func.lower(User.username) == username.lower())
    if exclude_id is not None:
        query = query.where(User.id != exclude_id)
    return (await session.execute(query)).scalar_one_or_none() is not None


@router.patch("/me", response_model=AccountUpdateResponse)
@limiter.limit(_settings.rate_limit_api)
async def update_me(
    request: Request,
    body: AccountUpdateRequest,
    user: Annotated[User, Depends(require_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountUpdateResponse:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta",
        )

    changes: dict[str, bool] = {"username": False, "password": False}

    if body.new_username is not None:
        new_username = body.new_username.strip()
        if not new_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nuevo usuario no puede estar vacío",
            )
        if len(new_username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nuevo usuario debe tener al menos 3 caracteres",
            )
        if new_username.lower() == user.username.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nuevo usuario debe ser distinto del actual",
            )
        if await _username_taken(session, new_username, exclude_id=user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya existe",
            )
        user.username = new_username
        changes["username"] = True

    if body.new_password is not None:
        user.password_hash = hash_password(body.new_password)
        changes["password"] = True

    if not changes["username"] and not changes["password"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indique un nuevo usuario o una nueva contraseña",
        )

    await log_audit(
        session,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        action="update_account",
        changes=changes,
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe",
        ) from exc

    return AccountUpdateResponse(id=user.id, username=user.username, role=user.role)
