"""Проверка того, что секреты не утекают наружу.

Охватывает: настройки приложения, ответы API, логи и отчёты.
"""

from __future__ import annotations

import io
import json
import logging

import httpx
import pytest

from app.core.config import settings
from app.providers.openrouter import OpenRouterProvider

SECRET = "sk-or-v1-секретный-ключ-1234567890"


class TestSettings:
    def test_api_key_is_not_a_plain_string(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
        from app.core.config import Settings

        fresh = Settings()
        assert fresh.openrouter_api_key.get_secret_value() == SECRET
        # В repr и при сериализации секрета нет.
        assert SECRET not in repr(fresh.openrouter_api_key)
        assert SECRET not in fresh.model_dump_json()

    def test_secret_value_accepts_plain_string(self):
        from app.core.config import secret_value

        assert secret_value(SECRET) == SECRET
        assert secret_value(None) == ""


class TestApiResponses:
    def test_settings_endpoint_does_not_expose_keys(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", SECRET)
        monkeypatch.setattr(settings, "llm_api_key", SECRET)
        monkeypatch.setattr(settings, "llm_provider", "openrouter")
        monkeypatch.setattr(settings, "openrouter_model", "example/model:free")

        response = client.get("/api/v1/settings/ai", headers=auth_headers)
        assert response.status_code == 200
        assert SECRET not in response.text
        assert "api_key" not in response.text.lower() or SECRET not in response.text

    def test_overview_does_not_expose_keys(self, client, auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", SECRET)
        response = client.get("/api/v1/overview", headers=auth_headers)
        assert SECRET not in response.text

    def test_provider_status_does_not_expose_key(self, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", SECRET)
        monkeypatch.setattr(settings, "openrouter_model", "example/model:free")
        status = OpenRouterProvider().status()
        assert SECRET not in json.dumps(status.__dict__, ensure_ascii=False)


class TestLogs:
    def test_key_is_not_written_to_logs(self, caplog):
        caplog.set_level(logging.DEBUG)
        logger = logging.getLogger("app.providers.openrouter")
        with caplog.at_level(logging.DEBUG):
            logger.warning("Ошибка провайдера: %s", "connection refused")
        assert SECRET not in caplog.text

    def test_http_error_logs_do_not_contain_authorization_header(self, caplog, monkeypatch):
        from app.providers.openai_client import OpenAICompatibleClient

        captured: dict = {}

        def _post(url, headers=None, json=None, timeout=None):
            captured["headers"] = headers or {}
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx, "post", _post)
        caplog.set_level(logging.DEBUG)
        client = OpenAICompatibleClient(
            base_url="https://example.test/v1", api_key=SECRET, model="m", max_retries=0
        )
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(Exception):
                client.chat("s", "u")
        assert SECRET not in caplog.text
        assert captured["headers"]["Authorization"] == f"Bearer {SECRET}"


class TestReport:
    def test_report_never_contains_key(self, client, auth_headers, product, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", SECRET)
        monkeypatch.setattr(settings, "llm_api_key", SECRET)
        run = client.post(
            f"/api/v1/products/{product['id']}/analysis-runs", headers=auth_headers
        ).json()
        report = client.get(
            f"/api/v1/products/{product['id']}/reports/{run['id']}", headers=auth_headers
        )
        assert report.status_code == 200
        assert SECRET not in report.text
