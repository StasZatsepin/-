"""Сравнение провайдеров анализа на фиксированном наборе утверждений.

Набор один и тот же для всех провайдеров (`app/backend/app/benchmarks/
claim_benchmark.json`), поэтому результаты сопоставимы. Скрипт показывает,
классифицирует ли провайдер утверждение так же, как ожидает ручная разметка.

Использование:
    .venv\\Scripts\\python.exe scripts\\compare_providers.py
    .venv\\Scripts\\python.exe scripts\\compare_providers.py --provider openrouter

Ключ OpenRouter берётся из переменных окружения (OPENROUTER_API_KEY,
OPENROUTER_MODEL). Если провайдер не настроен, сравнение честно
сообщает об этом и не выдумывает результат.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "app" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.benchmarks import BenchmarkCase, benchmark_metadata, load_benchmark  # noqa: E402
from app.models.enums import ClaimType  # noqa: E402
from app.providers.base import ClaimCandidate  # noqa: E402
from app.providers.registry import provider_chain  # noqa: E402


def _candidates(cases: List[BenchmarkCase]) -> List[ClaimCandidate]:
    return [
        ClaimCandidate(
            id=case.id,
            text=case.text,
            claim_type=ClaimType.OTHER.value,
            source_excerpt=case.text,
            source_name="Фиксированный набор",
            source_type="user_note",
        )
        for case in cases
    ]


def _score(provider, cases: List[BenchmarkCase]) -> Tuple[Dict[str, object], List[str]]:
    """Прогоняет набор через провайдера и считает совпадения."""
    result = provider.classify_claims(_candidates(cases), {"product_name": "Сравнение"})
    suggestions = {item.claim_id: item for item in result.claim_suggestions}

    type_hits = 0
    confidence_hits = 0
    misses: List[str] = []
    for case in cases:
        suggestion = suggestions.get(case.id)
        if suggestion is None:
            misses.append(f"{case.id}: нет предложения ({case.text[:40]})")
            continue
        if suggestion.claim_type == case.expected_type:
            type_hits += 1
        else:
            misses.append(
                f"{case.id}: тип {suggestion.claim_type} вместо {case.expected_type}"
            )
        if suggestion.confidence_label == case.expected_confidence:
            confidence_hits += 1

    total = len(cases) or 1
    return (
        {
            "provider": result.provider,
            "model": result.model_version,
            "status": result.status,
            "message": result.message,
            "type_accuracy": round(type_hits / total, 3),
            "confidence_accuracy": round(confidence_hits / total, 3),
            "answered": len(suggestions),
            "total": len(cases),
            "external": result.used_external_service,
        },
        misses,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        default="",
        help="Ограничить сравнение одним провайдером (mock, openrouter, ...)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вывести результат в JSON",
    )
    args = parser.parse_args()

    cases = load_benchmark()
    meta = benchmark_metadata()
    chain = provider_chain()

    if args.provider:
        wanted = args.provider.strip().lower()
        chain = [provider for provider in chain if provider.name == wanted]
        if not chain:
            print(
                f"Провайдер «{args.provider}» недоступен: активен "
                f"«{chain[0].name if chain else 'mock'}».",
                file=sys.stderr,
            )
            return 2

    report: List[Dict[str, object]] = []
    for provider in chain:
        summary, misses = _score(provider, cases)
        report.append(summary)
        if args.json:
            continue
        print(f"\n=== {summary['provider']} ({summary['model']}) ===")
        print(f"статус: {summary['status']} — {summary['message']}")
        print(
            "совпадение типа: {type_accuracy:.1%} · статус оценки: "
            "{confidence_accuracy:.1%} · ответов: {answered}/{total}".format(**summary)
        )
        for line in misses[:12]:
            print("  -", line)
        if len(misses) > 12:
            print(f"  ... ещё {len(misses) - 12}")

    if len(report) > 1:
        base, other = report[0], report[1]
        delta = float(other["type_accuracy"]) - float(base["type_accuracy"])
        print("\n=== разница ===")
        print(
            f"{other['provider']} против {base['provider']}: "
            f"{delta:+.1%} по совпадению типа"
        )

    if args.json:
        import json

        print(json.dumps({"benchmark": meta, "providers": report}, ensure_ascii=False, indent=2))
    else:
        print(f"\nНабор: {len(cases)} утверждений, версия {meta.get('version', '—')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
