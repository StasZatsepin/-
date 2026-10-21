"""Маршруты аутентификации и рабочего пространства."""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import create_access_token, get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.workspace import User, Workspace
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    WorkspaceOut,
)

logger = logging.getLogger("app.api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return base or "workspace"


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    counter = 1
    while db.execute(
        select(Workspace).where(Workspace.slug == slug)
    ).scalars().first() is not None:
        counter += 1
        slug = f"{base}-{counter}"
    return slug


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        workspace=WorkspaceOut(
            id=user.workspace.id,
            name=user.workspace.name,
            slug=user.workspace.slug,
            is_demo=user.workspace.is_demo,
        ),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Создаёт рабочее пространство и пользователя."""
    existing = db.execute(
        select(User).where(User.email == payload.email)
    ).scalars().first()
    if existing is not None:
        raise AppError("CONFLICT", "Пользователь с такой почтой уже зарегистрирован.")

    workspace = Workspace(
        name=payload.workspace_name or "Моё рабочее пространство",
        slug=_unique_slug(db, _slugify(payload.workspace_name or "workspace")),
        is_demo=False,
    )
    db.add(workspace)
    db.flush()

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.email.split("@")[0],
        role=UserRole.USER.value,
        workspace_id=workspace.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=settings.token_ttl_hours * 3600,
        user=_user_out(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Вход по электронной почте и паролю."""
    user = db.execute(select(User).where(User.email == payload.email)).scalars().first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("UNAUTHORIZED", "Неверная почта или пароль.")
    if not user.is_active:
        raise AppError("FORBIDDEN", "Учётная запись отключена.")
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=settings.token_ttl_hours * 3600,
        user=_user_out(user),
    )


@router.post("/demo", response_model=TokenResponse)
def demo_login(db: Session = Depends(get_db)) -> TokenResponse:
    """Вход в демонстрационное рабочее пространство."""
    if not settings.demo_mode:
        raise AppError(
            "FORBIDDEN",
            "Демо-режим выключен. Зарегистрируйтесь или войдите в рабочее пространство.",
        )
    from app.services.demo import ensure_demo_workspace

    user = ensure_demo_workspace(db)
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=settings.token_ttl_hours * 3600,
        user=_user_out(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    """Текущий пользователь и его рабочее пространство."""
    return _user_out(user)
