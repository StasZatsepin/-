"""Публичные маршруты без авторизации: быстрая проверка карточки."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.ratelimit import SlidingWindowLimiter
from app.db.session import get_db
from app.schemas.quick_check import QuickCheckRequest, QuickCheckResult
from app.services.quick_check import run_quick_check

router = APIRouter(prefix="/public", tags=["public"])

# 6 проверок в минуту и 40 в час с одного адреса
_per_minute = SlidingWindowLimiter(limit=6, window_seconds=60)
_per_hour = SlidingWindowLimiter(limit=40, window_seconds=3600)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/quick-check", response_model=QuickCheckResult)
def quick_check(
    payload: QuickCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> QuickCheckResult:
    """Проверяет введённый текст карточки встроенными правилами, ничего не сохраняя."""
    key = _client_key(request)
    if not (_per_minute.allow(key) and _per_hour.allow(key)):
        raise AppError(
            "RATE_LIMITED",
            "Слишком много проверок подряд. Подождите минуту и повторите.",
            status_code=429,
        )
    return run_quick_check(db, payload)
