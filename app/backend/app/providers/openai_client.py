"""Общий HTTP-клиент для провайдеров с OpenAI-совместимым API.

Отвечает за то, что одинаково нужно Ollama, OpenAI-совместимым сервисам и
OpenRouter: таймауты, ограниченные повторы с паузой, разбор ошибок
(429 / 401 / 404 / 5xx / сеть) и корректное извлечение текста ответа.

Секреты в этом модуле не попадают в логи: в журнал пишутся только класс
ошибки и код ответа.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("app.providers.http")

# Классификация ошибок: kind -> человекочитаемое объяснение для пользователя
ERROR_KINDS = {
    "rate_limited": "превышен лимит запросов (429). Бесплатные модели имеют ограничение по частоте запросов.",
    "unauthorized": "ключ API отклонён (401/403). Проверьте OPENROUTER_API_KEY.",
    "model_not_found": "модель не найдена (404). Проверьте идентификатор модели.",
    "bad_request": "запрос отклонён (400). Возможно, модель не поддерживает заданный формат ответа.",
    "server_error": "внутренняя ошибка сервиса (5xx).",
    "network": "нет связи с сервисом или истекло время ожидания.",
    "invalid_response": "сервис вернул ответ в неожиданном формате.",
}


@dataclass
class ProviderHTTPError(Exception):
    """Ошибка обращения к внешнему ИИ-сервису."""

    kind: str
    message: str
    status_code: Optional[int] = None
    retry_after: Optional[float] = None

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def user_message(self) -> str:
        return f"{self.message} ({ERROR_KINDS.get(self.kind, '')})".strip()


@dataclass
class ChatResult:
    """Успешный ответ чат-сервиса."""

    content: str
    model: str
    attempts: int
    usage: Dict[str, Any]


class OpenAICompatibleClient:
    """Минимальный клиент `/chat/completions` с повторами и разбором ошибок."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
        backoff: float = 2.0,
        extra_headers: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or ""
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.backoff = max(0.1, float(backoff))
        self.extra_headers = extra_headers or {}
        self.max_tokens = max_tokens

    # -- служебное ---------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        headers.update(self.extra_headers)
        return headers

    def _payload(self, system_prompt: str, user_prompt: str, json_mode: bool) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    @staticmethod
    def _retry_after(response: httpx.Response) -> Optional[float]:
        raw = response.headers.get("retry-after") if response is not None else None
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _error_kind(status_code: int) -> str:
        if status_code == 429:
            return "rate_limited"
        if status_code in (401, 403):
            return "unauthorized"
        if status_code == 404:
            return "model_not_found"
        if status_code == 400:
            return "bad_request"
        if status_code >= 500:
            return "server_error"
        return "bad_request"

    @staticmethod
    def _extract_content(data: Any) -> str:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise ProviderHTTPError(
                kind="invalid_response",
                message="Сервис вернул ответ без поля choices[0].message.content.",
            )
        content = message.get("content")
        if isinstance(content, list):
            # Некоторые сервисы возвращают content как список частей.
            parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") in (None, "text")
            ]
            content = "".join(parts)
        if not isinstance(content, str) or not content.strip():
            raise ProviderHTTPError(
                kind="invalid_response",
                message="Сервис вернул пустой ответ модели.",
            )
        return content

    # -- публичное ----------------------------------------------------------

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = True,
    ) -> ChatResult:
        """Выполняет запрос к /chat/completions с повторами при временных сбоях."""
        if not (self.base_url and self.api_key and self.model):
            raise ProviderHTTPError(
                kind="bad_request",
                message="Провайдер не настроен: нужны базовый URL, ключ и модель.",
            )

        url = f"{self.base_url}/chat/completions"
        attempts = self.max_retries + 1
        last_error: Optional[ProviderHTTPError] = None

        for attempt in range(1, attempts + 1):
            try:
                response = httpx.post(
                    url,
                    headers=self._headers(),
                    json=self._payload(system_prompt, user_prompt, json_mode),
                    timeout=self.timeout,
                )
            except httpx.TimeoutException:
                last_error = ProviderHTTPError(
                    kind="network",
                    message=f"Истекло время ожидания ответа ({self.timeout:g} с).",
                )
            except httpx.HTTPError as exc:
                last_error = ProviderHTTPError(
                    kind="network",
                    message=f"Сетевая ошибка при обращении к сервису ({type(exc).__name__}).",
                )
            else:
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except (ValueError, json.JSONDecodeError):
                        raise ProviderHTTPError(
                            kind="invalid_response",
                            message="Сервис вернул ответ, который не является JSON.",
                        )
                    return ChatResult(
                        content=self._extract_content(data),
                        model=str(data.get("model") or self.model),
                        attempts=attempt,
                        usage=data.get("usage") or {},
                    )

                kind = self._error_kind(response.status_code)
                last_error = ProviderHTTPError(
                    kind=kind,
                    message=f"Сервис ответил кодом {response.status_code}.",
                    status_code=response.status_code,
                    retry_after=self._retry_after(response),
                )
                # 4xx (кроме 429) повторять бессмысленно: запрос нужно менять.
                if response.status_code < 500 and kind != "rate_limited":
                    raise last_error

            if attempt < attempts:
                delay = last_error.retry_after if last_error and last_error.retry_after else None
                if delay is None:
                    delay = self.backoff * (2 ** (attempt - 1))
                logger.warning(
                    "Повтор запроса к ИИ-сервису (%s/%s): %s",
                    attempt,
                    attempts,
                    last_error.kind if last_error else "неизвестная ошибка",
                )
                time.sleep(min(delay, 30.0))

        assert last_error is not None
        raise last_error
