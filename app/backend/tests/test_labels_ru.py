"""Проверка полноты русских подписей: сырые коды не должны доходить до пользователя."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core import labels_ru
from app.models import enums

APP_ROOT = Path(__file__).resolve().parents[1] / "app"

ENUM_LABELS = [
    (enums.Marketplace, labels_ru.MARKETPLACE_LABELS),
    (enums.SourceType, labels_ru.SOURCE_TYPE_LABELS),
    (enums.ExtractionStatus, labels_ru.EXTRACTION_STATUS_LABELS),
    (enums.ExtractionMethod, labels_ru.EXTRACTION_METHOD_LABELS),
    (enums.ClaimType, labels_ru.CLAIM_TYPE_LABELS),
    (enums.EvidenceType, labels_ru.EVIDENCE_TYPE_LABELS),
    (enums.EvidenceRelation, labels_ru.EVIDENCE_RELATION_LABELS),
    (enums.FindingType, labels_ru.FINDING_TYPE_LABELS),
    (enums.Severity, labels_ru.SEVERITY_LABELS),
    (enums.FindingStatus, labels_ru.FINDING_STATUS_LABELS),
    (enums.ConfidenceStatus, labels_ru.CONFIDENCE_STATUS_LABELS),
    (enums.AnalysisStatus, labels_ru.ANALYSIS_STATUS_LABELS),
]

# Подпись не должна выглядеть как технический код.
RAW_CODE = re.compile(r"[a-z]+_[a-z_]+|[a-z]+\.[a-z_]+")


@pytest.mark.parametrize("enum_cls,mapping", ENUM_LABELS, ids=lambda value: getattr(value, "__name__", ""))
def test_every_enum_value_has_a_russian_label(enum_cls, mapping):
    missing = [member.value for member in enum_cls if member.value not in mapping]
    assert not missing, f"{enum_cls.__name__}: нет подписей для {missing}"


@pytest.mark.parametrize("enum_cls,mapping", ENUM_LABELS, ids=lambda value: getattr(value, "__name__", ""))
def test_labels_are_human_readable(enum_cls, mapping):
    for key, label in mapping.items():
        assert label.strip(), f"пустая подпись для {key}"
        assert not RAW_CODE.search(label), f"подпись похожа на технический код: {label!r}"
        assert re.search(r"[А-Яа-яЁё]", label) or label in {"Ozon", "Wildberries"}, (
            f"в подписи нет русского текста: {label!r}"
        )


def test_every_rule_id_used_by_the_engine_has_a_name():
    used: set[str] = set()
    for relative in ("rules/engine.py", "services/analysis.py"):
        source = (APP_ROOT / relative).read_text(encoding="utf-8")
        used.update(re.findall(r'rule_id\s*=\s*"([^"]+)"', source))
    assert used, "не найдено ни одного rule_id: проверьте регулярное выражение"
    missing = sorted(used - set(labels_ru.RULE_NAMES))
    assert not missing, f"нет понятных названий для правил: {missing}"


def test_unknown_value_never_returns_raw_code():
    assert labels_ru.label_for(labels_ru.SOURCE_TYPE_LABELS, "brand_new_type") == "Прочее"
    assert labels_ru.label_for(labels_ru.SOURCE_TYPE_LABELS, None) == "Прочее"
    assert labels_ru.rule_label("some.new_rule") == "Автоматическая проверка"
    assert labels_ru.rule_label(None) == "Автоматическая проверка"


def test_label_for_accepts_enum_members():
    assert labels_ru.label_for(labels_ru.FINDING_TYPE_LABELS, enums.FindingType.DIRECT_CONFLICT) == (
        "Прямое расхождение"
    )
