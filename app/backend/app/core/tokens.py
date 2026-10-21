"""Подписанные токены сессий (HMAC-SHA256) без внешних зависимостей."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from app.core.config import settings


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload_bytes: bytes) -> str:
    signature = hmac.new(
        settings.secret_key.encode("utf-8"), payload_bytes, hashlib.sha256
    ).digest()
    return _b64encode(signature)


def create_token(payload: Dict[str, Any], ttl_hours: Optional[int] = None) -> str:
    """Создаёт подписанный токен вида `payload.signature`."""
    ttl = settings.token_ttl_hours if ttl_hours is None else ttl_hours
    body = dict(payload)
    body["iat"] = int(time.time())
    body["exp"] = int(time.time()) + int(ttl) * 3600
    payload_bytes = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    encoded = _b64encode(payload_bytes)
    return f"{encoded}.{_sign(payload_bytes)}"


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Возвращает payload токена или None, если токен невалиден/просрочен."""
    if not token or "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    try:
        payload_bytes = _b64decode(encoded)
    except Exception:
        return None
    if not hmac.compare_digest(_sign(payload_bytes), signature):
        return None
    try:
        body = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if int(body.get("exp", 0)) < int(time.time()):
        return None
    return body
