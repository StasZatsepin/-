"""Координация конвейера анализа: источники -> утверждения -> находки."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_run import AnalysisRun
from app.models.claim import Claim
from app.models.enums import (
    AnalysisStatus,
    ClaimType,
    ConfidenceStatus,
    ExtractionMethod,
    FindingStatus,
    FindingType,
    SourceType,
)
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.product import Product
from app.models.source import Source
from app.providers.base import ClaimCandidate
from app.providers.registry import get_provider, run_provider
from app.rules.attributes import parse_attributes
from app.rules.engine import (
    RULES_VERSION,
    ComparableClaim,
    EvidenceRef,
    FindingDraft,
    build_ambiguous_findings,
    build_document_scope_findings,
    build_internal_conflict_findings,
    build_missing_evidence_findings,
    build_numeric_findings,
    build_review_signal_findings,
    build_unclassified_findings,
)
from app.rules.numeric import NumericStatement, find_qualifier
from app.services import sources as source_service
from app.services.claims import claims_for_source

logger = logging.getLogger("app.services.analysis")

AUTO_CLAIM_METHODS = {
    ExtractionMethod.RULE_BASED.value,
    ExtractionMethod.MOCK_PROVIDER.value,
    ExtractionMethod.LLM_PROVIDER.value,
    ExtractionMethod.SEEDED.value,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clear_generated_claims(db: Session, product_id: str) -> None:
    """Удаляет ранее сгенерированные утверждения, сохраняя ручные."""
    stmt = delete(Claim).where(
        Claim.product_id == product_id,
        Claim.extraction_method.in_(AUTO_CLAIM_METHODS),
    )
    db.execute(stmt)


def _clear_generated_evidence(db: Session, product_id: str) -> None:
    db.execute(delete(Evidence).where(Evidence.product_id == product_id))


def _archive_previous_findings(db: Session, product_id: str) -> None:
    """Архивирует нерассмотренные авто-находки предыдущих запусков."""
    stmt = select(Finding).where(
        Finding.product_id == product_id,
        Finding.archived.is_(False),
        Finding.origin.in_(["rules", "mock", "llm"]),
        Finding.status.in_([FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value]),
    )
    for finding in db.execute(stmt).scalars():
        finding.archived = True
    db.flush()


def _persist_claims(
    db: Session, product: Product, sources: List[Source]
) -> List[Claim]:
    claims: List[Claim] = []
    for source in sources:
        drafts = claims_for_source(
            source.source_type, source.text_content or "", source.metadata_json or {}
        )
        for draft in drafts:
            claim = Claim(
                product_id=product.id,
                workspace_id=product.workspace_id,
                source_id=source.id,
                text=draft.text,
                claim_type=draft.claim_type,
                source_excerpt=draft.source_excerpt,
                start_offset=draft.start_offset,
                end_offset=draft.end_offset,
                extraction_method=draft.extraction_method,
                model_version=draft.model_version,
                confidence_label=draft.confidence_label,
                confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                numeric_value=draft.numeric_value,
                numeric_unit=draft.numeric_unit,
                numeric_dimension=draft.numeric_dimension,
                numeric_comparator=draft.numeric_comparator,
                numeric_context=draft.numeric_context,
            )
            db.add(claim)
            claims.append(claim)
    db.flush()
    return claims


def _apply_provider_suggestions(claims: List[Claim], suggestions) -> int:
    """Применяет предложения провайдера к типам утверждений."""
    by_id = {claim.id: claim for claim in claims}
    applied = 0
    for suggestion in suggestions:
        claim = by_id.get(suggestion.claim_id)
        if claim is None or claim.user_confirmed:
            continue
        if suggestion.claim_type != ClaimType.OTHER.value:
            claim.claim_type = suggestion.claim_type
            claim.extraction_method = (
                ExtractionMethod.LLM_PROVIDER.value
                if suggestion.provider in {"ollama", "openai_compatible"}
                else ExtractionMethod.MOCK_PROVIDER.value
            )
            claim.model_version = suggestion.model_version or None
            applied += 1
        if suggestion.confidence_label:
            claim.confidence_label = suggestion.confidence_label
            if suggestion.confidence_label in {
                ConfidenceStatus.SUBJECTIVE.value,
                ConfidenceStatus.NEEDS_REVIEW.value,
                ConfidenceStatus.INSUFFICIENT.value,
                ConfidenceStatus.CONFLICTING.value,
                ConfidenceStatus.SUPPORTED.value,
            }:
                claim.confidence_status = suggestion.confidence_label
    return applied


def _build_comparables(claims: List[Claim], sources: List[Source]) -> List[ComparableClaim]:
    source_by_id = {source.id: source for source in sources}
    comparables: List[ComparableClaim] = []
    for claim in claims:
        if claim.is_rejected or claim.numeric_value is None or not claim.numeric_dimension:
            continue
        source = source_by_id.get(claim.source_id) if claim.source_id else None
        statement = NumericStatement(
            value=float(claim.numeric_value),
            unit_key=claim.numeric_unit or "",
            dimension=claim.numeric_dimension,
            comparator=claim.numeric_comparator or "exact",
            raw_text=claim.text,
            sentence=claim.text,
            qualifier=find_qualifier(claim.text),
            context=claim.numeric_context or claim.text,
        )
        comparables.append(
            ComparableClaim(
                claim_id=claim.id,
                text=claim.text,
                source_id=claim.source_id,
                source_name=getattr(source, "source_name", "Неизвестный источник"),
                source_type=getattr(source, "source_type", SourceType.OTHER.value),
                statement=statement,
            )
        )
    return comparables


def _build_evidence(
    db: Session,
    product: Product,
    claims: List[Claim],
    comparables: List[ComparableClaim],
    eligible_claim_ids: Optional[set] = None,
) -> Tuple[Dict[str, List[str]], set]:
    """Создаёт записи доказательств.

    Возвращает (карта claim_id -> id доказательств, множество утверждений,
    по которым уже есть подтверждение или зафиксировано расхождение).
    Для них отдельная находка «нет подтверждения» не создаётся.
    """
    from app.rules.attributes import parse_attribute
    from app.rules.engine import match_attribute
    from app.rules.units import convert

    attributes = dict(product.attributes or {})
    quantities, _skipped = parse_attributes(attributes)
    sources = list(
        db.execute(select(Source).where(Source.product_id == product.id)).scalars()
    )
    source_by_id = {source.id: source for source in sources}
    attribute_source = source_service.find_system_source(
        db, product.id, SourceType.ATTRIBUTE_SHEET.value
    )

    evidence_ids: Dict[str, List[str]] = {}
    supported: set = set()
    contradicted: set = set()

    for claim in claims:
        if claim.is_rejected:
            continue
        source = source_by_id.get(claim.source_id) if claim.source_id else None
        evidence_type = "description_text"
        if source is not None:
            if source.source_type == SourceType.REVIEW_EXPORT.value:
                evidence_type = "review_statement"
            elif source.source_type == SourceType.TECHNICAL_DOCUMENT.value:
                evidence_type = "document_statement"
            elif source.source_type == SourceType.ATTRIBUTE_SHEET.value:
                evidence_type = "attribute_value"
            elif source.source_type == SourceType.USER_NOTE.value:
                evidence_type = "user_note"

        evidence = Evidence(
            product_id=product.id,
            workspace_id=product.workspace_id,
            source_id=claim.source_id,
            claim_id=claim.id,
            evidence_type=evidence_type,
            excerpt=claim.source_excerpt or claim.text,
            relation="contextualizes",
            relevance_note="Фрагмент источника, на который опирается утверждение.",
            date=source.source_date if source else None,
        )
        db.add(evidence)
        db.flush()
        evidence_ids.setdefault(claim.id, []).append(evidence.id)

    # Связываем числовые утверждения с таблицей характеристик
    for comparable in comparables:
        if comparable.source_type == SourceType.ATTRIBUTE_SHEET.value:
            supported.add(comparable.claim_id)
            continue
        if eligible_claim_ids is not None and comparable.claim_id not in eligible_claim_ids:
            continue
        matched = match_attribute(comparable.statement, comparable.text, quantities)
        if matched is None:
            continue
        quantity, _score = matched
        converted = convert(
            comparable.statement.value, comparable.statement.unit_key, quantity.unit_key
        )
        if converted is None:
            continue
        if abs(converted - quantity.value) <= max(abs(quantity.value) * 0.03, 0.01):
            relation = "supports"
            note = "Значение подтверждается таблицей характеристик."
            supported.add(comparable.claim_id)
        else:
            relation = "contradicts"
            note = "Значение расходится с таблицей характеристик."
            contradicted.add(comparable.claim_id)
        evidence = Evidence(
            product_id=product.id,
            workspace_id=product.workspace_id,
            source_id=attribute_source.id if attribute_source else None,
            claim_id=comparable.claim_id,
            evidence_type="attribute_value",
            excerpt=f"{quantity.label}: {quantity.raw_value}",
            relation=relation,
            relevance_note=note,
        )
        db.add(evidence)
        db.flush()
        evidence_ids.setdefault(comparable.claim_id, []).append(evidence.id)

    return evidence_ids, supported | contradicted


def _persist_findings(
    db: Session,
    product: Product,
    run: AnalysisRun,
    drafts,
    evidence_ids: Dict[str, List[str]],
) -> List[Finding]:
    findings: List[Finding] = []
    for draft in drafts:
        ids: List[str] = []
        if draft.claim_id:
            ids.extend(evidence_ids.get(draft.claim_id, []))
        ids = list(dict.fromkeys(ids))

        finding = Finding(
            product_id=product.id,
            workspace_id=product.workspace_id,
            claim_id=draft.claim_id,
            analysis_run_id=run.id,
            finding_type=draft.finding_type,
            severity=draft.severity,
            title=draft.title,
            description=draft.description,
            source_evidence_ids=ids,
            source_refs=[ref.to_dict() for ref in draft.evidence],
            limitations=draft.limitations,
            recommended_action=draft.recommended_action,
            confidence_status=draft.confidence_status,
            status=FindingStatus.OPEN.value,
            rule_id=draft.rule_id,
            rule_version=draft.rule_version,
            origin=draft.origin,
            explanation=draft.explanation,
            explanation_provider=draft.explanation_provider,
        )
        db.add(finding)
        findings.append(finding)
    db.flush()
    return findings


def run_analysis(
    db: Session, product: Product, user_email: str = ""
) -> AnalysisRun:
    """Выполняет полный анализ товара и сохраняет результаты."""
    run = AnalysisRun(
        product_id=product.id,
        workspace_id=product.workspace_id,
        status=AnalysisStatus.RUNNING.value,
        engine_version=settings.app_version,
        rules_version=RULES_VERSION,
        provider_name=(settings.llm_provider or "mock"),
        triggered_by=user_email,
        started_at=_utcnow(),
    )
    db.add(run)
    db.flush()

    try:
        source_service.sync_system_sources(db, product)
        all_sources = list(
            db.execute(select(Source).where(Source.product_id == product.id)).scalars()
        )

        _clear_generated_claims(db, product.id)
        _clear_generated_evidence(db, product.id)
        db.flush()

        claims = _persist_claims(db, product, all_sources)
        manual_claims = list(
            db.execute(
                select(Claim).where(
                    Claim.product_id == product.id,
                    Claim.extraction_method == ExtractionMethod.MANUAL.value,
                )
            ).scalars()
        )
        claims = list(claims) + list(manual_claims)

        source_by_id = {source.id: source for source in all_sources}

        # --- классификация через провайдера (по умолчанию локальная эвристика) ---
        provider = get_provider()
        candidates: List[ClaimCandidate] = []
        for claim in claims:
            if claim.claim_type != ClaimType.OTHER.value:
                continue
            source = source_by_id.get(claim.source_id) if claim.source_id else None
            candidates.append(
                ClaimCandidate(
                    id=claim.id,
                    text=claim.text,
                    claim_type=claim.claim_type,
                    source_excerpt=claim.source_excerpt,
                    source_name=getattr(source, "source_name", "Источник товара"),
                    source_type=getattr(source, "source_type", SourceType.OTHER.value),
                    source_id=claim.source_id,
                )
            )

        provider_result, used_external = run_provider(
            provider,
            candidates,
            {
                "product_name": product.name,
                "product_description": product.description or "",
            },
        )
        applied = _apply_provider_suggestions(claims, provider_result.claim_suggestions)

        # --- дополнительные утверждения от модели ---
        # Модель дополняет детерминированный разбор, но её утверждения
        # принимаются только с дословным фрагментом источника.
        extracted_by_provider = _extract_claims_with_provider(
            db, product, provider, all_sources, claims, source_by_id
        )
        claims = list(claims) + extracted_by_provider

        comparables = _build_comparables(claims, all_sources)
        eligible_claim_ids = _eligible_claim_ids(
            claims, source_by_id, dict(product.attributes or {})
        )
        evidence_ids, supported_claims = _build_evidence(
            db, product, claims, comparables, eligible_claim_ids
        )

        quantities, skipped_attributes = parse_attributes(dict(product.attributes or {}))
        attribute_claims = _attribute_claim_map(claims, quantities)

        review_claims = [
            claim
            for claim in claims
            if claim.source_id
            and getattr(source_by_id.get(claim.source_id), "source_type", "")
            == SourceType.REVIEW_EXPORT.value
        ]

        drafts = []
        drafts.extend(
            build_numeric_findings(
                comparables, quantities, attribute_claims, eligible_claim_ids
            )
        )
        drafts.extend(build_internal_conflict_findings(comparables, quantities))
        drafts.extend(build_ambiguous_findings(claims))
        drafts.extend(
            build_missing_evidence_findings(
                claims,
                supported_claims,
                {
                    claim.id: getattr(
                        source_by_id.get(claim.source_id), "source_type", SourceType.OTHER.value
                    )
                    for claim in claims
                },
            )
        )
        drafts.extend(build_review_signal_findings(review_claims, comparables))
        drafts.extend(
            build_document_scope_findings(all_sources, dict(product.attributes or {}))
        )
        drafts.extend(
            build_unclassified_findings(
                claims,
                {SourceType.PRODUCT_DESCRIPTION.value, SourceType.USER_NOTE.value},
            )
        )

        for suggestion in provider_result.finding_suggestions:
            draft = _finding_draft_from_provider(suggestion, all_sources)
            if draft is not None:
                drafts.append(draft)

        # --- пояснения модели к находкам ---
        # Пояснение дополняет формулировку, но не меняет тип, серьёзность
        # и статус находки: их определяют детерминированные правила.
        explained = _explain_findings_with_provider(
            provider, drafts, product, all_sources
        )
        for index, draft in enumerate(drafts):
            explanation = explained.get(str(index))
            if explanation:
                draft.explanation = explanation.text
                draft.explanation_provider = explanation.provider

        _archive_previous_findings(db, product.id)
        findings = _persist_findings(db, product, run, drafts, evidence_ids)

        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for finding in findings:
            by_type[finding.finding_type] = by_type.get(finding.finding_type, 0) + 1
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1

        limitations: List[str] = [
            "Автоматическая проверка выполняется только по предоставленным материалам.",
        ]
        if skipped_attributes:
            limitations.append(
                "Не сопоставлены с единицами измерения характеристики: "
                + ", ".join(sorted(skipped_attributes)[:10])
                + "."
            )
        if not used_external:
            limitations.append(
                "Внешний ИИ-провайдер не использовался: анализ выполнен "
                "детерминированными правилами."
            )
        if extracted_by_provider:
            limitations.append(
                "Часть утверждений извлечена моделью и требует подтверждения "
                "пользователем."
            )
        if provider_result.message:
            limitations.append(provider_result.message)

        run.status = AnalysisStatus.COMPLETED.value
        run.finished_at = _utcnow()
        run.provider_status = provider_result.message
        run.summary = {
            "product_name": product.name,
            "claims_total": len(claims),
            "claims_sent_to_provider": provider_result.claims_sent,
            "claims_not_classified_due_to_limit": max(
                0, len(candidates) - provider_result.claims_sent
            ),
            "claims_classified_by_provider": applied,
            "claims_rejected_by_provider": provider_result.claims_rejected,
            "claims_extracted_by_provider": len(extracted_by_provider),
            "sources_total": len(all_sources),
            "findings_total": len(findings),
            "findings_by_type": by_type,
            "findings_by_severity": by_severity,
            "findings_explained_by_provider": len(explained),
            "provider": provider_result.provider,
            "provider_model": provider_result.model_version,
            "provider_ok": provider_result.status in {"ok", "empty"},
            "external_service_used": used_external,
            "evidence_total": sum(len(value) for value in evidence_ids.values()),
        }
        run.limitations = limitations
        db.flush()
        return run
    except Exception as exc:
        logger.exception("Анализ товара %s завершился ошибкой", product.id)
        run.status = AnalysisStatus.FAILED.value
        run.finished_at = _utcnow()
        run.error_message = f"{type(exc).__name__}: анализ не завершён."
        db.flush()
        raise


def _product_model(attributes: Dict[str, object]) -> str:
    """Ищет значение модели/артикула среди характеристик товара."""
    for key, value in (attributes or {}).items():
        lowered = str(key).lower()
        if "model" in lowered or "артикул" in lowered or "арт" == lowered:
            return str(value)
    return ""


def _eligible_claim_ids(
    claims: List[Claim], source_by_id: Dict[str, Source], attributes: Dict[str, object]
) -> set:
    """Отбирает утверждения, которые можно сравнивать с характеристиками товара.

    Отзывы не сравниваются с таблицей характеристик (это пользовательские
    сигналы), а документы с областью применения другой модели исключаются:
    для них создаётся отдельная находка о несовпадении области применения.
    """
    product_model = _product_model(attributes).lower()
    eligible: set = set()
    for claim in claims:
        source = source_by_id.get(claim.source_id) if claim.source_id else None
        if source is None:
            continue
        if source.source_type == SourceType.ATTRIBUTE_SHEET.value:
            continue
        if source.source_type == SourceType.REVIEW_EXPORT.value:
            continue
        if source.source_type == SourceType.TECHNICAL_DOCUMENT.value:
            metadata = source.metadata_json or {}
            applies_to = str(metadata.get("applies_to_model") or "").strip().lower()
            if applies_to and product_model and applies_to != product_model:
                continue
        eligible.add(claim.id)
    return eligible


def _attribute_claim_map(claims: List[Claim], quantities) -> Dict[str, str]:
    """Сопоставляет ключ характеристики с идентификатором утверждения."""
    result: Dict[str, str] = {}
    for claim in claims:
        if claim.numeric_dimension is None:
            continue
        lowered = (claim.text or "").lower().replace(" ", "_")
        for quantity in quantities:
            if quantity.dimension != claim.numeric_dimension:
                continue
            if quantity.label.replace(" ", "_") in lowered:
                result.setdefault(quantity.key, claim.id)
                break
    return result


def _finding_draft_from_provider(suggestion, sources):
    """Создаёт находку из предложения модели.

    Предложение принимается, только если модель процитировала фрагмент,
    который дословно есть в одном из источников. Тип находки принудительно
    меняется на `needs_human_review`: модель не вправе объявлять факт
    доказанным.
    """
    from app.models.enums import FindingType, Severity

    source_texts = [
        (source.source_name, source.text_content or "") for source in sources
    ]
    excerpts = [excerpt for excerpt in (suggestion.excerpts or []) if excerpt.strip()]
    verified = [
        excerpt
        for excerpt in excerpts
        if any(excerpt in text for _, text in source_texts)
    ]
    if not verified:
        logger.info(
            "Предложение модели отклонено: нет дословного фрагмента источника"
        )
        return None

    return FindingDraft(
        finding_type=FindingType.NEEDS_HUMAN_REVIEW.value,
        severity=Severity.LOW.value,
        title=suggestion.title[:250],
        description=suggestion.description,
        claim_id=suggestion.claim_id,
        evidence=[
            EvidenceRef(
                source_id=None,
                source_name=source_name,
                excerpt=excerpt,
                relation="uncertain",
                note="Фрагмент приведён моделью и подтверждён в исходном источнике.",
            )
            for source_name, text in source_texts
            for excerpt in verified
            if excerpt in text
        ][:5],
        limitations=(
            "Вывод предложен языковой моделью и требует проверки человеком: "
            "подтверждение факта требует сверки с первоисточником."
        ),
        recommended_action=suggestion.recommended_action
        or "Проверить вывод по первоисточникам.",
        confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
        rule_id="provider.suggestion",
        origin="llm",
    )


def _normalize_claim_text(text: str) -> str:
    """Нормализует текст для сравнения утверждений (без пунктуации и регистра)."""
    lowered = (text or "").lower().replace("ё", "е")
    return " ".join(
        "".join(char if char.isalnum() or char.isspace() else " " for char in lowered).split()
    )


def _extract_claims_with_provider(
    db: Session,
    product: Product,
    provider,
    sources: List[Source],
    claims: List[Claim],
    source_by_id: Dict[str, Source],
) -> List[Claim]:
    """Дополняет детерминированный разбор утверждениями, найденными моделью.

    Принимаются только утверждения с дословным фрагментом источника, которых
    ещё нет среди найденных правилами.
    """
    if not getattr(provider, "uses_external_service", False):
        return []

    existing = {_normalize_claim_text(claim.text) for claim in claims}
    created: List[Claim] = []

    for source in sources:
        text = source.text_content or ""
        if not text.strip():
            continue
        try:
            extracted = provider.extract_claims(
                text,
                {
                    "product_name": product.name,
                    "source_name": source.source_name,
                },
            )
        except Exception as exc:  # pragma: no cover - защита от сбоя провайдера
            logger.warning(
                "Провайдер %s не смог извлечь утверждения: %s",
                provider.name,
                type(exc).__name__,
            )
            continue

        for item in extracted:
            excerpt = (item.source_excerpt or "").strip()
            if not excerpt or excerpt not in text:
                continue
            normalized = _normalize_claim_text(item.text)
            if not normalized or normalized in existing:
                continue
            existing.add(normalized)

            claim = Claim(
                product_id=product.id,
                workspace_id=product.workspace_id,
                source_id=source.id,
                text=item.text[:2000],
                claim_type=item.claim_type,
                source_excerpt=excerpt,
                extraction_method=ExtractionMethod.LLM_PROVIDER.value,
                model_version=getattr(provider, "model", "") or None,
                confidence_label=item.confidence_label,
                confidence_status=item.confidence_label,
                user_confirmed=False,
                numeric_context=excerpt,
            )
            db.add(claim)
            created.append(claim)

    db.flush()
    return created


def _explain_findings_with_provider(provider, drafts, product, sources) -> Dict[str, object]:
    """Запрашивает у модели пояснения к находкам.

    Возвращает словарь {индекс находки: пояснение}. Пояснение не влияет на
    тип и серьёзность находки — их определяют детерминированные правила.
    """
    if not getattr(provider, "uses_external_service", False) or not drafts:
        return {}

    from app.providers.base import FindingContext

    contexts: List[FindingContext] = []
    for index, draft in enumerate(drafts[:20]):
        contexts.append(
            FindingContext(
                rule_id=draft.rule_id,
                title=draft.title,
                description=draft.description[:1500],
                evidence_excerpts=[ref.excerpt for ref in draft.evidence[:5]],
                limitations=draft.limitations,
                key=str(index),
            )
        )

    try:
        suggestions = provider.explain_findings(
            contexts,
            {"product_name": product.name},
        )
    except Exception as exc:  # pragma: no cover - защита от сбоя провайдера
        logger.warning(
            "Провайдер %s не смог объяснить находки: %s",
            provider.name,
            type(exc).__name__,
        )
        return {}

    by_key = {str(index): draft for index, draft in enumerate(drafts[:20])}
    result: Dict[str, object] = {}
    for suggestion in suggestions:
        draft = by_key.get(str(suggestion.rule_id))
        if draft is None:
            continue
        result[str(suggestion.rule_id)] = _ModelExplanation(
            text=suggestion.explanation,
            provider=provider.name,
        )
    return result


@dataclass
class _ModelExplanation:
    text: str
    provider: str
