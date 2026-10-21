"""Зависимости FastAPI: текущий пользователь, рабочее пространство, доступ к ресурсам."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.tokens import create_token, decode_token
from app.db.session import get_db
from app.models.analysis_run import AnalysisRun
from app.models.claim import Claim
from app.models.finding import Finding
from app.models.product import Product
from app.models.source import Source
from app.models.workspace import User, Workspace


def create_access_token(user: User) -> str:
    return create_token(
        {
            "sub": user.id,
            "ws": user.workspace_id,
            "email": user.email,
            "role": user.role,
        }
    )


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Возвращает пользователя по токену. Без корректного токена — 401."""
    token = _extract_bearer(authorization)
    if not token:
        raise AppError(
            "UNAUTHORIZED", "Требуется вход в систему. Передайте токен в заголовке Authorization."
        )
    payload = decode_token(token)
    if not payload:
        raise AppError("UNAUTHORIZED", "Сессия недействительна или истекла. Войдите заново.")
    user = db.get(User, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise AppError("UNAUTHORIZED", "Пользователь не найден или отключён.")
    return user


def get_current_workspace(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Workspace:
    workspace = db.get(Workspace, user.workspace_id)
    if workspace is None:
        raise AppError("NOT_FOUND", "Рабочее пространство не найдено.")
    return workspace


def get_owned_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Product:
    """Возвращает товар только если он принадлежит рабочему пространству пользователя."""
    product = db.get(Product, product_id)
    if product is None or product.workspace_id != user.workspace_id:
        raise AppError("NOT_FOUND", "Товар не найден.")
    return product


def get_owned_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Source:
    source = db.get(Source, source_id)
    if source is None or source.workspace_id != user.workspace_id:
        raise AppError("NOT_FOUND", "Источник не найден.")
    return source


def get_owned_finding(
    finding_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Finding:
    finding = db.get(Finding, finding_id)
    if finding is None or finding.workspace_id != user.workspace_id:
        raise AppError("NOT_FOUND", "Находка не найдена.")
    return finding


def get_owned_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None or run.workspace_id != user.workspace_id:
        raise AppError("NOT_FOUND", "Запуск анализа не найден.")
    return run


def get_owned_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None or claim.workspace_id != user.workspace_id:
        raise AppError("NOT_FOUND", "Утверждение не найдено.")
    return claim


def list_workspace_products(db: Session, user: User):
    return list(
        db.execute(
            select(Product).where(Product.workspace_id == user.workspace_id)
        ).scalars()
    )


__all__ = [
    "create_access_token",
    "get_current_user",
    "get_current_workspace",
    "get_owned_claim",
    "get_owned_finding",
    "get_owned_product",
    "get_owned_run",
    "get_owned_source",
    "list_workspace_products",
    "settings",
]
