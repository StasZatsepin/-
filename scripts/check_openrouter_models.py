"""Проверка идентификаторов моделей OpenRouter по официальным данным.

Скрипт обращается к публичному эндпоинту `GET /api/v1/models` (ключ не
нужен) и показывает:
  * существует ли модель, указанная в конфигурации;
  * является ли она бесплатной (цен�� `pricing.prompt == 0`);
  * какие модели бесплатны прямо сейчас.

Использование:
    .venv\\Scripts\\python.exe scripts\\check_openrouter_models.py
    .venv\\Scripts\\python.exe scripts\\check_openrouter_models.py --model minimax/minimax-m3.1-flash:free
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "app" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

MODELS_URL = "https://openrouter.ai/api/v1/models"


def fetch_models(timeout: float = 45.0) -> List[Dict[str, Any]]:
    response = httpx.get(MODELS_URL, timeout=timeout)
    response.raise_for_status()
    return response.json().get("data", [])


def is_free(model: Dict[str, Any]) -> bool:
    """Модель бесплатна по цене (prompt и completion равны нулю)."""
    pricing = model.get("pricing") or {}
    try:
        return float(pricing.get("prompt") or 0) == 0.0 and float(
            pricing.get("completion") or 0
        ) == 0.0
    except (TypeError, ValueError):
        return False


def is_free_tier(model: Dict[str, Any]) -> bool:
    """Бесплатный тариф OpenRouter: идентификатор с суффиксом `:free`.

    Именно этот признак означает «модель в бесплатной очереди», а не
    «цена сейчас равна нулю».
    """
    return str(model.get("id", "")).endswith(":free")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="", help="Проверить конкретную модель")
    parser.add_argument("--all", action="store_true", help="Показать все бесплатные модели")
    args = parser.parse_args()

    try:
        models = fetch_models()
    except Exception as exc:
        print(f"Не удалось получить список моделей: {type(exc).__name__}", file=sys.stderr)
        return 2

    free = [model for model in models if is_free(model)]
    free_tier = [model for model in models if is_free_tier(model)]
    print(f"Моделей всего: {len(models)}")
    print(f"  с нулевой ценой: {len(free)} · в бесплатной очереди (:free): {len(free_tier)}")

    if args.all:
        print("\nБесплатные модели сейчас (нулевая цена):")
        for model in sorted(free, key=lambda item: item["id"]):
            tier = ":free" if is_free_tier(model) else "цена 0"
            print(f"  - {model['id']} [{tier}] (контекст {model.get('context_length')})")

    target = args.model
    if not target:
        from app.core.config import settings

        target = settings.openrouter_model or ""

    if target:
        print(f"\nПроверяем модель из конфигурации: {target or '(не задана)'}")
        if not target:
            print("  Модель не задана: укажите OPENROUTER_MODEL в окружении.")
            return 1
        match = next((model for model in models if model["id"] == target), None)
        if match is None:
            print("  Модель не найдена в каталоге OpenRouter.")
            print("  Доступные бесплатные модели перечислены выше (--all).")
            return 1
        free_flag = (
            "бесплатная очередь (:free)"
            if is_free_tier(match)
            else ("нулевая цена" if is_free(match) else "ПЛАТНАЯ")
        )
        print(f"  Найдена: {match['id']} · {free_flag} · контекст {match.get('context_length')}")
        if not is_free(match):
            print(
                "  Внимание: модель не бесплатна. Проверьте идентификатор или "
                "выберите модель с суффиксом :free."
            )
            return 1
        if not is_free_tier(match):
            print(
                "  Внимание: у модели нет суффикса :free — она не обязана быть "
                "в бесплатной очереди OpenRouter."
            )
        supported = match.get("supported_parameters") or []
        if "response_format" in supported:
            print("  Поддерживает структурированный ответ (response_format).")
        else:
            print("  Структурированный ответ не заявлен: ответ будет разобран как JSON.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
