"""Отчёт не содержит сырых технических кодов и разделителя « · ».

Тест не требует базы данных: данные для шаблона собираются функцией
``build_report_context`` из обычных объектов.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.reports import ENVIRONMENT, build_report_context

RAW_CODES = re.compile(
    r"technical_document|review_export|product_description|attribute_sheet|user_note"
    r"|needs_human_review|needs_ocr|contextualizes|uncertain|contradicts|unrelated"
    r"|supported_by_provided_source|conflicting_sources|insufficient_evidence"
    r"|subjective_or_not_testable|direct_conflict|missing_evidence|review_signal"
    r"|ambiguous_claim|document_scope_mismatch|rule_based|mock_provider"
    r"|claims\.[a-z_]+|evidence\.[a-z_]+|reviews\.[a-z_]+|documents\.[a-z_]+|numeric\.[a-z_]+"
)


def _build_html() -> str:
    now = datetime(2026, 11, 2, 11, 30, tzinfo=timezone.utc)
    midnight = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)

    product = SimpleNamespace(
        name="ДЕМО: беспроводные наушники X-500",
        category="Электроника",
        marketplace="demo",
        sku="DEMO-500",
        is_demo=True,
    )
    run = SimpleNamespace(
        rules_version="rules-2024.1",
        provider_name="mock",
        status="completed",
        finished_at=now,
        limitations=[],
        summary={},
    )
    sources = [
        SimpleNamespace(
            id="s1",
            source_name="ДЕМО-СЕРТИФИКАТ",
            source_type="technical_document",
            source_date=midnight,
            created_at=now,
            content_hash="a" * 64,
            extraction_status="extracted",
            extraction_note="",
            size_bytes=10,
            metadata_json={"demo": True},
        ),
        SimpleNamespace(
            id="s2",
            source_name="ДЕМО-ВЫГРУЗКА ОТЗЫВОВ",
            source_type="review_export",
            source_date=None,
            created_at=now,
            content_hash="b" * 64,
            extraction_status="needs_ocr",
            extraction_note="",
            size_bytes=10,
            metadata_json={},
        ),
    ]
    claims = [
        SimpleNamespace(
            id="c1",
            text="До 48 часов работы без подзарядки",
            claim_type="numeric_performance",
            source_id="s1",
            confidence_status="needs_human_review",
            user_confirmed=False,
            is_rejected=False,
        )
    ]
    findings = [
        SimpleNamespace(
            id="f1",
            title="Обещание сформулировано неопределённо",
            finding_type="ambiguous_claim",
            severity="info",
            status="open",
            description="В тексте найдена формулировка «идеально».",
            limitations="Нет объективного критерия.",
            recommended_action="Заменить на проверяемое утверждение.",
            confidence_status="subjective_or_not_testable",
            rule_id="claims.ambiguous_promise",
            rule_version="rules-2024.1",
            source_refs=[
                {"source_name": "ДЕМО-СЕРТИФИКАТ", "excerpt": "Время работы — 30 часов.", "relation": "contextualizes"},
                {"source_name": "ДЕМО-ВЫГРУЗКА ОТЗЫВОВ", "excerpt": "Батарея держится 20 часов.", "relation": "uncertain"},
            ],
        ),
        SimpleNamespace(
            id="f2",
            title="Нет подтверждения",
            finding_type="missing_evidence",
            severity="medium",
            status="in_review",
            description="Утверждение не подтверждено.",
            limitations="",
            recommended_action="",
            confidence_status="insufficient_evidence",
            rule_id="evidence.missing_confirmation",
            rule_version="rules-2024.1",
            source_refs=[],
        ),
    ]
    actions = [
        SimpleNamespace(
            created_at=now,
            user_email="demo@local.test",
            previous_status="open",
            new_status="in_review",
            comment="Проверяю",
            finding_id="f1",
        )
    ]
    context = build_report_context(product, run, sources, claims, findings, actions)
    return ENVIRONMENT.get_template("report.html.j2").render(**context)


def _without_technical_blocks(html: str) -> str:
    return re.sub(r"<details class=\"tech\">.*?</details>", "", html, flags=re.S)


def test_report_has_no_raw_codes_outside_technical_blocks():
    visible = _without_technical_blocks(_build_html())
    found = sorted(set(RAW_CODES.findall(visible)))
    assert not found, f"в отчёте остались сырые коды: {found}"


def test_report_technical_block_keeps_rule_id_for_reproducibility():
    html = _build_html()
    assert "claims.ambiguous_promise" in html
    assert "Обещание без объективного критерия" in html


def test_report_has_no_dot_separators():
    assert " · " not in _build_html()


def test_report_dates_without_time_when_midnight():
    html = _build_html()
    assert "15.03.2026" in html
    assert "15.03.2026 00:00" not in html


def test_report_uses_russian_labels():
    html = _build_html()
    for expected in ("Технический документ", "Отзывы", "Демо", "уточняет контекст", "неопределённо"):
        assert expected in html, expected
