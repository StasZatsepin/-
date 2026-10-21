"""Тесты провайдера OpenRouter: схема ответа, ошибки, повторы, секреты.

Сеть не используется: HTTP-вызовы подменяются заглушкой.
"""

from __future__ import annotations

import json
import json as json_lib

import httpx
import pytest

from app.core.config import settings
from app.models.enums import ClaimType
from app.providers.base import ClaimCandidate, FindingContext
from app.providers.openai_client import ProviderHTTPError
from app.providers.openrouter import OpenRouterProvider

MODEL = "example/model:free"


def _candidate(index: str = "c1", text: str = "До 48 часов работы.") -> ClaimCandidate:
    return ClaimCandidate(
        id=index,
        text=text,
        claim_type=ClaimType.OTHER.value,
        source_excerpt=text,
        source_name="Описание товара",
        source_type="product_description",
    )


def _response(payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=payload,
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}], "model": MODEL}


@pytest.fixture()
def provider(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-secret-key")
    monkeypatch.setattr(settings, "openrouter_model", MODEL)
    monkeypatch.setattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(settings, "openrouter_timeout_seconds", 5.0)
    monkeypatch.setattr(settings, "openrouter_max_retries", 2)
    monkeypatch.setattr(settings, "openrouter_retry_backoff_seconds", 0.01)
    monkeypatch.setattr(settings, "openrouter_fallback_models", [])
    return OpenRouterProvider()


class TestConfiguration:
    def test_provider_disabled_without_key(self, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "")
        monkeypatch.setattr(settings, "openrouter_model", MODEL)
        provider = OpenRouterProvider()
        status = provider.status()
        assert status.available is False
        assert status.requires_api_key is True
        assert status.external_data_transfer is True
        assert "OPENROUTER_API_KEY" in status.message

    def test_provider_disabled_without_model(self, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "key")
        monkeypatch.setattr(settings, "openrouter_model", "")
        provider = OpenRouterProvider()
        assert provider.status().available is False

    def test_status_never_contains_the_key(self, provider):
        blob = json.dumps(provider.status().__dict__, ensure_ascii=False)
        assert "test-secret-key" not in blob


class TestClassification:
    def test_successful_classification(self, provider, monkeypatch):
        content = json.dumps(
            {
                "claims": [
                    {
                        "id": "c1",
                        "claim_type": "numeric_performance",
                        "confidence_label": "conflicting_sources",
                        "rationale": "Есть числовое обещание.",
                    }
                ]
            }
        )
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _response(_completion(content)))

        result = provider.classify_claims([_candidate()], {"product_name": "Товар"})
        assert result.status == "ok"
        assert result.used_external_service is True
        assert len(result.claim_suggestions) == 1
        suggestion = result.claim_suggestions[0]
        assert suggestion.claim_type == "numeric_performance"
        assert suggestion.confidence_label == "conflicting_sources"

    def test_invalid_claim_type_is_dropped(self, provider, monkeypatch):
        content = json.dumps(
            {"claims": [{"id": "c1", "claim_type": "выдуманный_тип"}]}
        )
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _response(_completion(content)))

        result = provider.classify_claims([_candidate()], {})
        assert result.status == "empty"
        assert result.claim_suggestions == []

    def test_invalid_json_is_reported_as_unavailable(self, provider, monkeypatch):
        monkeypatch.setattr(
            httpx, "post", lambda *a, **k: _response(_completion("не json вовсе"))
        )
        result = provider.classify_claims([_candidate()], {})
        assert result.status == "unavailable"
        assert "схем" in result.message.lower() or "json" in result.message.lower()

    def test_schema_violation_is_reported(self, provider, monkeypatch):
        monkeypatch.setattr(
            httpx,
            "post",
            lambda *a, **k: _response(_completion(json.dumps({"claims": "не список"}))),
        )
        result = provider.classify_claims([_candidate()], {})
        assert result.status == "unavailable"

    def test_network_failure_is_reported(self, provider, monkeypatch):
        def _boom(*args, **kwargs):
            raise httpx.ConnectError("connection refused")

        monkeypatch.setattr(httpx, "post", _boom)
        result = provider.classify_claims([_candidate()], {})
        assert result.status == "unavailable"
        assert "OpenRouter недоступен" in result.message


class TestRetriesAndRateLimit:
    def test_429_is_retried_and_then_falls_back_to_next_model(
        self, provider, monkeypatch
    ):
        monkeypatch.setattr(settings, "openrouter_fallback_models", ["example/backup:free"])
        # Список резервных моделей читается при создании провайдера.
        provider = OpenRouterProvider()
        calls: list[str] = []

        def _post(url, headers=None, json=None, timeout=None):
            model = json["model"]
            calls.append(model)
            if model == MODEL:
                return httpx.Response(
                    status_code=429,
                    json={"error": {"message": "rate limit"}},
                    request=httpx.Request("POST", str(url)),
                )
            return _response(
                _completion(
                    json_lib.dumps(
                        {
                            "claims": [
                                {
                                    "id": "c1",
                                    "claim_type": "numeric_performance",
                                    "confidence_label": "needs_human_review",
                                }
                            ]
                        }
                    )
                )
            )

        monkeypatch.setattr(httpx, "post", _post)
        result = provider.classify_claims([_candidate()], {})

        assert result.status == "ok"
        assert MODEL in calls
        assert "example/backup:free" in calls

    def test_retries_are_limited(self, provider, monkeypatch):
        attempts: list[int] = []

        def _post(url, headers=None, json=None, timeout=None):
            attempts.append(1)
            return httpx.Response(
                status_code=500,
                json={"error": "boom"},
                request=httpx.Request("POST", str(url)),
            )

        monkeypatch.setattr(httpx, "post", _post)
        result = provider.classify_claims([_candidate()], {})
        assert result.status == "unavailable"
        # max_retries = 2 -> не более трёх попыток
        assert len(attempts) <= settings.openrouter_max_retries + 1

    def test_401_is_not_retried(self, provider, monkeypatch):
        attempts: list[int] = []

        def _post(url, headers=None, json=None, timeout=None):
            attempts.append(1)
            return httpx.Response(
                status_code=401,
                json={"error": "unauthorized"},
                request=httpx.Request("POST", str(url)),
            )

        monkeypatch.setattr(httpx, "post", _post)
        result = provider.classify_claims([_candidate()], {})
        assert result.status == "unavailable"
        assert len(attempts) == 1


class TestExtraction:
    def test_only_claims_with_verbatim_excerpt_are_kept(self, provider, monkeypatch):
        content = json.dumps(
            {
                "claims": [
                    {
                        "text": "Наушники держат заряд 30 часов.",
                        "claim_type": "numeric_performance",
                        "source_excerpt": "заряд 30 часов",
                        "confidence_label": "supported_by_provided_source",
                    },
                    {
                        "text": "Сертификат выдан на модель X.",
                        "claim_type": "certification_or_compliance",
                        "source_excerpt": "этого фрагмента нет в тексте",
                    },
                ]
            }
        )
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _response(_completion(content)))

        text = "Наушники держат заряд 30 часов."
        extracted = provider.extract_claims(text, {"product_name": "Товар"})
        assert len(extracted) == 1
        assert extracted[0].source_excerpt == "заряд 30 часов"

    def test_extraction_without_model_returns_nothing(self, monkeypatch):
        monkeypatch.setattr(settings, "openrouter_api_key", "")
        provider = OpenRouterProvider()
        assert provider.extract_claims("любой текст", {}) == []


class TestExplanations:
    def test_only_verified_quotes_are_kept(self, provider, monkeypatch):
        content = json.dumps(
            {
                "explanations": [
                    {
                        "rule_id": "0",
                        "explanation": "Значения расходятся.",
                        "quotes": ["До 48 часов работы", "выдуманная цитата"],
                    }
                ]
            }
        )
        monkeypatch.setattr(httpx, "post", lambda *a, **k: _response(_completion(content)))

        contexts = [
            FindingContext(
                rule_id="numeric.attribute_comparison",
                title="Расхождение",
                description="48 против 30",
                evidence_excerpts=["До 48 часов работы"],
                key="0",
            )
        ]
        explanations = provider.explain_findings(contexts, {})
        assert len(explanations) == 1
        assert explanations[0].quotes == ["До 48 часов работы"]


class TestErrorMessages:
    def test_rate_limit_message_is_actionable(self, provider, monkeypatch):
        monkeypatch.setattr(
            httpx,
            "post",
            lambda url, headers=None, json=None, timeout=None: httpx.Response(
                status_code=429,
                json={"error": "slow down"},
                request=httpx.Request("POST", str(url)),
            ),
        )
        result = provider.classify_claims([_candidate()], {})
        assert "429" in result.message or "лимит" in result.message.lower()

    def test_model_not_found_message_is_actionable(self, provider, monkeypatch):
        monkeypatch.setattr(
            httpx,
            "post",
            lambda url, headers=None, json=None, timeout=None: httpx.Response(
                status_code=404,
                json={"error": "no model"},
                request=httpx.Request("POST", str(url)),
            ),
        )
        result = provider.classify_claims([_candidate()], {})
        assert "404" in result.message

    def test_error_message_never_contains_the_key(self, provider, monkeypatch):
        monkeypatch.setattr(
            httpx,
            "post",
            lambda url, headers=None, json=None, timeout=None: httpx.Response(
                status_code=401,
                json={"error": {"message": "bad key sk-test-secret-key"}},
                request=httpx.Request("POST", str(url)),
            ),
        )
        result = provider.classify_claims([_candidate()], {})
        assert "test-secret-key" not in result.message


class TestClient:
    def test_missing_configuration_raises_clear_error(self):
        from app.providers.openai_client import OpenAICompatibleClient

        client = OpenAICompatibleClient(base_url="", api_key="", model="")
        with pytest.raises(ProviderHTTPError) as excinfo:
            client.chat("s", "u")
        assert excinfo.value.kind == "bad_request"

    def test_authorization_header_uses_bearer(self, provider, monkeypatch):
        captured: dict = {}

        def _post(url, headers=None, json=None, timeout=None):
            captured.update(headers or {})
            return _response(_completion(json_lib.dumps({"claims": []})))

        monkeypatch.setattr(httpx, "post", _post)
        provider.classify_claims([_candidate()], {})
        assert captured["Authorization"] == "Bearer test-secret-key"
