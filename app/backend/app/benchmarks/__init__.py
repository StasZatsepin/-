"""Загрузка фиксированного набора для сравнения провайдеров анализа."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

BENCHMARK_PATH = Path(__file__).resolve().parent / "claim_benchmark.json"


@dataclass
class BenchmarkCase:
    """Один пример набора с ожидаемой разметкой."""

    id: str
    text: str
    expected_type: str
    expected_confidence: str


def load_benchmark(path: Optional[Path] = None) -> List[BenchmarkCase]:
    """Читает набор из JSON. Файл неизменяем: это основа сравнения."""
    source = path or BENCHMARK_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    return [
        BenchmarkCase(
            id=item["id"],
            text=item["text"],
            expected_type=item["expected_type"],
            expected_confidence=item["expected_confidence"],
        )
        for item in payload.get("claims", [])
    ]


def benchmark_metadata(path: Optional[Path] = None) -> Dict[str, str]:
    source = path or BENCHMARK_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    return {
        "version": str(payload.get("version", "")),
        "description": str(payload.get("description", "")),
    }
