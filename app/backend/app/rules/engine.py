"""Детерминированный движок проверок.

Модуль не зависит от внешнего ИИ: все находки вычисляются из предоставленных
источников. Каждая находка содержит ссылку на источник и фрагмент, а также
явное ограничение, чтобы выводы не выдавались за доказанные факты.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.models.enums import (
    ConfidenceStatus,
    FindingType,
    Severity,
    SourceType,
)
from app.rules.attributes import AttributeQuantity
from app.rules.numeric import NumericStatement, unit_display
from app.rules.patterns import (
    find_ambiguous_marker,
    is_ambiguous_claim,
    review_sentiment,
)

RULES_VERSION = "rules-2024.1"

# Относительный допуск при сравнении чисел (3 % + абсолютная поправка)
RELATIVE_TOLERANCE = 0.03
ABSOLUTE_TOLERANCE = 0.01

# Токены ключей, которые являются единицами измерения, а не смыслом параметра
_UNIT_TOKENS = {
    "hours", "hour", "h", "hrs", "min", "minute", "kg", "g", "mg", "mm", "cm", "m",
    "w", "v", "gb", "tb", "mb", "mah", "ah", "l", "ml", "pcs", "db",
    "seconds", "days", "months", "years", "value", "capacity", "size",
}

# Ведущие слова по измерению: помогают связать утверждение с характеристикой
DIMENSION_HINTS: Dict[str, Tuple[str, ...]] = {
    "time": ("час", "минут", "дн", "время", "работ", "автоном", "заряд", "срок", "месяц"),
    "mass": ("вес", "масс", "кг", "г."),
    "length": ("размер", "длин", "ширин", "высот", "толщин", "диаметр", "см", "мм"),
    "storage": ("памят", "gb", "гб", "tb", "тб", "rom", "оператив"),
    "charge": ("ёмк", "емк", "mah", "аккумулятор", "заряд"),
    "power": ("мощност", "ватт", "вт"),
    "voltage": ("напряжен", "вольт"),
    "volume": ("объем", "объём", "литр", "л.", "мл"),
    "count": ("штук", "шт", "количеств", "комплект"),
    "percent": ("процент", "%"),
    "level": ("шум", "дб"),
    "temperature": ("температур", "градус"),
}

# Синонимы для ключей характеристик
ATTRIBUTE_KEY_HINTS: Dict[str, Tuple[str, ...]] = {
    "battery_life": ("батаре", "заряд", "автоном", "время работы", "наработк", "работ"),
    "battery": ("батаре", "аккумулятор", "заряд"),
    "runtime": ("работ", "автоном"),
    "warranty": ("гарант", "срок"),
    "weight": ("вес", "масс"),
    "length": ("длин", "размер"),
    "width": ("ширин",),
    "height": ("высот",),
    "power": ("мощност",),
    "voltage": ("напряжен",),
    "capacity": ("ёмк", "емк", "аккумулятор"),
    "storage": ("памят",),
    "noise": ("шум",),
    "temperature": ("температур",),
}

# Типы утверждений, для которых в принципе возможно подтверждение
VERIFIABLE_CLAIM_TYPES = {
    "numeric_performance",
    "dimension_or_weight",
    "compatibility",
    "material_or_composition",
    "certification_or_compliance",
    "warranty_or_service",
}

# Типы утверждений, где автоматическая проверка неуместна
HIGH_RISK_CLAIM_TYPES = {"safety_or_health"}


@dataclass
class EvidenceRef:
    """Ссылка на источник в находке."""

    source_id: Optional[str]
    source_name: str
    excerpt: str
    relation: str
    evidence_type: str = "description_text"
    note: str = ""

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "excerpt": self.excerpt,
            "relation": self.relation,
            "evidence_type": self.evidence_type,
            "note": self.note,
        }


@dataclass
class FindingDraft:
    """Черновик находки до сохранения в базе."""

    finding_type: str
    severity: str
    title: str
    description: str
    claim_id: Optional[str] = None
    evidence: List[EvidenceRef] = field(default_factory=list)
    limitations: str = ""
    recommended_action: str = ""
    confidence_status: str = ConfidenceStatus.NEEDS_REVIEW.value
    rule_id: str = ""
    rule_version: str = RULES_VERSION
    origin: str = "rules"
    # Пояснение внешней модели: не меняет тип и серьёзность находки,
    # а только дополняет её формулировкой.
    explanation: str = ""
    explanation_provider: str = ""


@dataclass
class ComparableClaim:
    """Утверждение с числовым значением, пригодное для сравнения."""

    claim_id: str
    text: str
    source_id: Optional[str]
    source_name: str
    source_type: str
    statement: NumericStatement


def values_differ(first: float, second: float) -> bool:
    """Проверяет, отличаются ли значения за пределами допуска."""
    if abs(first - second) <= ABSOLUTE_TOLERANCE:
        return False
    scale = max(abs(first), abs(second), 1e-9)
    return abs(first - second) / scale > RELATIVE_TOLERANCE


def _specific_hint_words(quantity: AttributeQuantity) -> List[str]:
    """Маркеры, которые указывают именно на эту характеристику."""
    words: List[str] = []
    tokens = quantity.key.split("_")

    # Многословные ключи целиком: `battery_life` → «время работы», «батарея».
    for size in (3, 2):
        for index in range(len(tokens) - size + 1):
            phrase = "_".join(tokens[index : index + size])
            words.extend(ATTRIBUTE_KEY_HINTS.get(phrase, ()))

    for token in tokens:
        words.extend(ATTRIBUTE_KEY_HINTS.get(token, ()))
        if token not in _UNIT_TOKENS:
            words.append(token)
    return words


def match_attribute(
    statement: NumericStatement, claim_text: str, quantities: Sequence[AttributeQuantity]
) -> Optional[Tuple[AttributeQuantity, float]]:
    """Подбирает характеристику, сопоставимую с числовым утверждением.

    Связь устанавливается только при совпадении маркеров конкретной
    характеристики (например, «батарея», «вес») в фрагменте текста рядом
    с числом. Общие слова измерения (часы, граммы) слишком слабы: по ним
    нельзя понять, о каком именно параметре идёт речь.
    """
    candidates = [q for q in quantities if q.dimension == statement.dimension]
    if not candidates:
        return None
    haystack = (statement.context or claim_text or "").lower()
    best: Optional[Tuple[AttributeQuantity, float]] = None
    for quantity in candidates:
        score = 0.0
        for word in _specific_hint_words(quantity):
            if word and word in haystack:
                score += 2.0 if len(word) > 4 else 1.0
        if score <= 0:
            continue
        if best is None or score > best[1]:
            best = (quantity, score)
    return best


def _convert(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    from app.rules.units import convert

    return convert(value, from_unit, to_unit)


def _comparable(
    claim_value: float, claim_comparator: str, spec_value: float, spec_comparator: str
) -> Tuple[bool, str]:
    """Определяет, создаёт ли пара значений расхождение.

    Возвращает (есть_расхождение, тип_расхождения).
    """
    if claim_comparator == "exact" and spec_comparator == "exact":
        if values_differ(claim_value, spec_value):
            ratio = abs(claim_value - spec_value) / max(abs(spec_value), 1e-9)
            return True, "exact_mismatch"
        return False, ""

    if claim_comparator == "up_to":
        if claim_value > spec_value and values_differ(claim_value, spec_value):
            return True, "promise_exceeds_spec"
        return False, ""

    if claim_comparator == "from":
        if spec_value < claim_value and values_differ(claim_value, spec_value):
            return True, "spec_below_promise"
        return False, ""

    if claim_comparator == "over":
        if spec_value <= claim_value and values_differ(claim_value, spec_value):
            return True, "spec_below_promise"
        return False, ""

    if claim_comparator == "under":
        if spec_value >= claim_value and values_differ(claim_value, spec_value):
            return True, "spec_above_promise"
        return False, ""

    if claim_comparator == "about":
        if values_differ(claim_value, spec_value):
            return True, "approximate"
        return False, ""

    if claim_comparator == "range":
        lower = 0.0
        if spec_value < lower or spec_value > claim_value:
            if values_differ(claim_value, spec_value):
                return True, "range"
        return False, ""

    return False, ""


def _severity_for_mismatch(kind: str) -> str:
    if kind == "exact_mismatch":
        return Severity.MEDIUM.value
    if kind in {"promise_exceeds_spec", "spec_below_promise"}:
        return Severity.MEDIUM.value
    return Severity.LOW.value


def _format_value(value: float, unit_key: str) -> str:
    from app.rules.numeric import unit_display

    return f"{value:g} {unit_display(unit_key)}"


def build_numeric_findings(
    comparables: Sequence[ComparableClaim],
    quantities: Sequence[AttributeQuantity],
    attribute_claims: Dict[str, str],
    eligible_claim_ids: Optional[set] = None,
) -> List[FindingDraft]:
    """Сравнивает числовые утверждения с характеристиками и другими источниками.

    `eligible_claim_ids` ограничивает сравнение только теми утверждениями,
    которые действительно относятся к этому товару: отзывы и документы,
    относящиеся к другой модели, сравниваются отдельно.
    """
    findings: List[FindingDraft] = []
    seen: set = set()

    for comparable in comparables:
        if eligible_claim_ids is not None and comparable.claim_id not in eligible_claim_ids:
            continue
        statement = comparable.statement
        matched = match_attribute(statement, comparable.text, quantities)
        if matched is None:
            continue
        quantity, _score = matched
        converted = _convert(statement.value, statement.unit_key, quantity.unit_key)
        if converted is None:
            continue

        attribute_claim_id = attribute_claims.get(quantity.key)
        spec_value = quantity.value
        has_mismatch, kind = _comparable(
            converted, statement.comparator, spec_value, "exact"
        )
        if not has_mismatch:
            continue

        has_conditions = bool(statement.has_qualifier)
        if kind == "approximate" or has_conditions:
            finding_type = FindingType.NEEDS_HUMAN_REVIEW.value
            severity = Severity.LOW.value if kind == "approximate" else Severity.MEDIUM.value
            title = "Требуется проверка: значения числового параметра расходятся"
            limitations = (
                "Условия измерения в источниках не указаны или значения сравниваются "
                "приблизительно. Расхождение может объясняться разными режимами работы "
                "или погрешностью округления. Это не доказательство ложности утверждения."
            )
        else:
            finding_type = FindingType.DIRECT_CONFLICT.value
            severity = _severity_for_mismatch(kind)
            title = "Числовое расхождение между описанием и характеристиками"
            limitations = (
                "Значения взяты из предоставленных материалов. Условия измерения "
                "не приводятся, поэтому требуется подтверждение продавца: "
                "расхождение может объясняться разными режимами работы."
            )

        key = (comparable.claim_id, quantity.key)
        if key in seen:
            continue
        seen.add(key)

        description = (
            f"В описании товара указано: «{statement.describe()}» "
            f"({comparable.source_name}).\n"
            f"В таблице характеристик: {quantity.label} = "
            f"{_format_value(quantity.value, quantity.unit_key)}.\n"
            f"Расхождение: {abs(converted - spec_value):g} "
            f"{unit_display(quantity.unit_key)} "
            f"({'значение обещания выше' if converted > spec_value else 'значение обещания ниже'})."
        )

        findings.append(
            FindingDraft(
                finding_type=finding_type,
                severity=severity,
                title=title,
                description=description,
                claim_id=comparable.claim_id,
                evidence=[
                    EvidenceRef(
                        source_id=comparable.source_id,
                        source_name=comparable.source_name,
                        excerpt=comparable.text,
                        relation="contradicts",
                        evidence_type="description_text",
                        note="Утверждение продавца из описания товара.",
                    ),
                    EvidenceRef(
                        source_id=None,
                        source_name="Таблица характеристик товара",
                        excerpt=f"{quantity.label}: {quantity.raw_value}",
                        relation="contradicts",
                        evidence_type="attribute_value",
                        note="Структурированная характеристика, загруженная пользователем.",
                    ),
                ],
                limitations=limitations,
                recommended_action=(
                    "Проверить условия измерения и привести описание в соответствие "
                    "с подтверждёнными характеристиками либо приложить документ, "
                    "подтверждающий заявленное значение."
                ),
                confidence_status=(
                    ConfidenceStatus.CONFLICTING.value
                    if finding_type == FindingType.DIRECT_CONFLICT.value
                    else ConfidenceStatus.NEEDS_REVIEW.value
                ),
                rule_id="numeric.attribute_comparison",
            )
        )

    return findings


def build_internal_conflict_findings(
    comparables: Sequence[ComparableClaim],
    quantities: Sequence[AttributeQuantity],
) -> List[FindingDraft]:
    """Ищет противоречия между двумя утверждениями одного источника.

    Сравниваются только утверждения об одном и том же параметре: иначе
    «гарантия 24 месяца» и «ответ в течение 1 часа» были бы ложным
    противоречием.
    """
    findings: List[FindingDraft] = []
    for index, first in enumerate(comparables):
        for second in comparables[index + 1 :]:
            if first.source_id != second.source_id:
                continue
            if first.claim_id == second.claim_id:
                continue
            if first.statement.dimension != second.statement.dimension:
                continue
            if first.statement.comparator != "exact" or second.statement.comparator != "exact":
                continue
            if not values_differ(first.statement.value, second.statement.value):
                continue

            first_match = match_attribute(first.statement, first.text, quantities)
            second_match = match_attribute(second.statement, second.text, quantities)
            if first_match is None or second_match is None:
                continue
            if first_match[0].key != second_match[0].key:
                continue

            findings.append(
                FindingDraft(
                    finding_type=FindingType.NEEDS_HUMAN_REVIEW.value,
                    severity=Severity.MEDIUM.value,
                    title="Внутри одного источника указаны разные значения параметра",
                    description=(
                        f"В источнике «{first.source_name}» параметр "
                        f"({first_match[0].label}) указан как "
                        f"«{first.statement.describe()}» и «{second.statement.describe()}».\n"
                        "Требуется уточнить, к какому из значений относится товар."
                    ),
                    claim_id=first.claim_id,
                    evidence=[
                        EvidenceRef(
                            source_id=first.source_id,
                            source_name=first.source_name,
                            excerpt=first.text,
                            relation="uncertain",
                        ),
                        EvidenceRef(
                            source_id=second.source_id,
                            source_name=second.source_name,
                            excerpt=second.text,
                            relation="uncertain",
                        ),
                    ],
                    limitations=(
                        "Противоречие внутри одного материала может объясняться "
                        "описанием разных вариантов товара."
                    ),
                    recommended_action=(
                        "Уточнить описание и привести значения к однозначной формулировке."
                    ),
                    confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                    rule_id="numeric.internal_consistency",
                )
            )
    return findings


def build_ambiguous_findings(claims: Iterable) -> List[FindingDraft]:
    """Находит абсолютные и субъективные обещания, которые нельзя проверить."""
    findings: List[FindingDraft] = []
    for claim in claims:
        text = claim.text or ""
        marker = _find_marker(text)
        if marker is None:
            continue
        findings.append(
            FindingDraft(
                finding_type=FindingType.AMBIGUOUS_CLAIM.value,
                severity=Severity.INFO.value,
                title="Обещание сформулировано неопределённо",
                description=(
                    f"В тексте найдена формулировка «{marker}»: {_quote(text)}.\n"
                    "Такое утверждение не имеет объективного критерия проверки, "
                    "поэтому подтвердить или опровергнуть его по предоставленным данным нельзя."
                ),
                claim_id=claim.id,
                evidence=[
                    EvidenceRef(
                        source_id=claim.source_id,
                        source_name=_source_name(claim),
                        excerpt=text,
                        relation="contextualizes",
                    )
                ],
                limitations=(
                    "Формулировка оценочная или абсолютная. Это не признак обмана: "
                    "просто автоматическая проверка по документам невозможна."
                ),
                recommended_action=(
                    "Переформулировать утверждение через проверяемые параметры "
                    "или приложить документ, подтверждающий заявленный эффект."
                ),
                confidence_status=ConfidenceStatus.SUBJECTIVE.value,
                rule_id="claims.ambiguous_promise",
            )
        )
    return findings


def _find_marker(text: str) -> Optional[str]:
    return find_ambiguous_marker(text)


def _quote(text: object) -> str:
    """Цитата в кавычках «ёлочках» без хвостовой точки: точка ставится после кавычки."""
    cleaned = " ".join(str(text).split()).rstrip(" .;,!…")
    return f"«{cleaned}»"


def _value_note(text: object, value_text: str) -> str:
    """Значение в скобках, только если его ещё нет в цитате (иначе получится дубль)."""
    normalized = " ".join(str(text).split()).lower()
    if value_text.strip().lower() in normalized:
        return ""
    return f" ({value_text})"


def _source_name(claim) -> str:
    source = getattr(claim, "source", None)
    return getattr(source, "source_name", "Неизвестный источник") if source else "Неизвестный источник"


def build_missing_evidence_findings(
    claims: Iterable,
    supported_claim_ids: set,
    source_types_by_claim: Dict[str, str],
) -> List[FindingDraft]:
    """Находит проверяемые утверждения без предоставленного подтверждения."""
    findings: List[FindingDraft] = []
    for claim in claims:
        if claim.id in supported_claim_ids:
            continue
        source_type = source_types_by_claim.get(claim.id, "")
        if source_type not in {SourceType.PRODUCT_DESCRIPTION.value}:
            continue
        claim_type = claim.claim_type

        if claim_type in HIGH_RISK_CLAIM_TYPES:
            findings.append(
                FindingDraft(
                    finding_type=FindingType.NEEDS_HUMAN_REVIEW.value,
                    severity=Severity.MEDIUM.value,
                    title="Утверждение о безопасности требует проверки человеком",
                    description=(
                        f"В описании товара есть утверждение: {_quote(claim.text)}.\n"
                        "Подтверждающих документов по этому утверждению не предоставлено. "
                        "Такие заявления нельзя подтвердить или опровергнуть автоматически."
                    ),
                    claim_id=claim.id,
                    evidence=[
                        EvidenceRef(
                            source_id=claim.source_id,
                            source_name=_source_name(claim),
                            excerpt=claim.text,
                            relation="contextualizes",
                        )
                    ],
                    limitations=(
                        "Отсутствие подтверждения не означает ложность утверждения. "
                        "Требуется проверка специалистом и подтверждающий документ."
                    ),
                    recommended_action=(
                        "Проверить утверждение с профильным специалистом и приложить "
                        "подтверждающий документ либо убрать формулировку."
                    ),
                    confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                    rule_id="evidence.missing_safety_confirmation",
                )
            )
            continue

        if claim_type not in VERIFIABLE_CLAIM_TYPES:
            continue

        findings.append(
            FindingDraft(
                finding_type=FindingType.MISSING_EVIDENCE.value,
                severity=Severity.LOW.value,
                title="Для утверждения не предоставлено подтверждение",
                description=(
                    f"Утверждение из описания товара: {_quote(claim.text)}.\n"
                    "В предоставленных материалах нет документа, подтверждающего это "
                    "утверждение. Проверка выполнена по доступным данным."
                ),
                claim_id=claim.id,
                evidence=[
                    EvidenceRef(
                        source_id=claim.source_id,
                        source_name=_source_name(claim),
                        excerpt=claim.text,
                        relation="contextualizes",
                    )
                ],
                limitations=(
                    "Отсутствие подтверждения не является доказательством ложности "
                    "утверждения: документ мог просто не быть загружен."
                ),
                recommended_action=(
                    "Загрузить подтверждающий документ, зафиксировать дату его действия "
                    "и область применимости либо переформулировать утверждение."
                ),
                confidence_status=ConfidenceStatus.INSUFFICIENT.value,
                rule_id="evidence.missing_confirmation",
            )
        )
    return findings


def build_review_signal_findings(
    review_claims: Iterable,
    comparables: Sequence[ComparableClaim],
) -> List[FindingDraft]:
    """Формирует сигналы из отзывов покупателей."""
    findings: List[FindingDraft] = []
    sentiments: Dict[str, List] = {}

    for claim in review_claims:
        sentiment = review_sentiment(claim.text)
        sentiments.setdefault(sentiment, []).append(claim)

    negative = sentiments.get("negative", [])
    if negative:
        for claim in negative[:10]:
            findings.append(
                FindingDraft(
                    finding_type=FindingType.REVIEW_SIGNAL.value,
                    severity=Severity.LOW.value,
                    title="Отзыв покупателя содержит возможное расхождение",
                    description=(
                        f"Отзыв: {_quote(claim.text)}.\n"
                        "В отзыве упоминается расхождение с ожиданиями покупателя. "
                        "Показан как пользовательский сигнал, а не как установленный факт."
                    ),
                    claim_id=claim.id,
                    evidence=[
                        EvidenceRef(
                            source_id=claim.source_id,
                            source_name=_source_name(claim),
                            excerpt=claim.text,
                            relation="contextualizes",
                            evidence_type="review_statement",
                            note="Отзыв покупателя (синхронизация из файла отзывов).",
                        )
                    ],
                    limitations=(
                        "Отзыв — субъективный опыт одного покупателя. Он не является "
                        "доказательством дефекта и не подтверждает нарушение."
                    ),
                    recommended_action=(
                        "Сопоставить отзыв с описанием товара и проверить, "
                        "раскрывается ли спорный параметр в карточке."
                    ),
                    confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                    rule_id="reviews.negative_signal",
                )
            )

    mixed = sentiments.get("mixed", [])
    # Противоположные мнения в наборе отзывов — тоже смешанный сигнал.
    if sentiments.get("negative") and sentiments.get("positive"):
        mixed = mixed or (sentiments["negative"][:3] + sentiments["positive"][:3])
    if mixed:
        excerpts = "\n".join(f"— {_quote(claim.text)}" for claim in mixed[:5])
        findings.append(
            FindingDraft(
                finding_type=FindingType.REVIEW_SIGNAL.value,
                severity=Severity.INFO.value,
                title="В отзывах встречаются противоположные мнения",
                description=(
                    "Часть отзывов указывает на расхождения, часть — на соответствие "
                    "ожиданиям. Разные оценки одного и того же параметра:\n" + excerpts
                ),
                claim_id=mixed[0].id,
                evidence=[
                    EvidenceRef(
                        source_id=claim.source_id,
                        source_name=_source_name(claim),
                        excerpt=claim.text,
                        relation="contextualizes",
                        evidence_type="review_statement",
                    )
                    for claim in mixed[:5]
                ],
                limitations=(
                    "Отзывы не являются независимыми подтверждениями: их количество "
                    "нельзя использовать как статистику без проверки уникальности "
                    "и происхождения."
                ),
                recommended_action=(
                    "Изучить отзывы по конкретному параметру и при необходимости "
                    "добавить в карточку уточняющую информацию."
                ),
                confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                rule_id="reviews.mixed_signal",
            )
        )

    # Числовые расхождения, упомянутые в негативном или смешанном отзыве
    for claim in review_claims:
        sentiment = review_sentiment(claim.text)
        if sentiment not in {"negative", "mixed"}:
            continue
        statement = getattr(claim, "numeric_dimension", None)
        if not statement:
            continue
        for comparable in comparables:
            if comparable.statement.dimension != claim.numeric_dimension:
                continue
            if comparable.source_type == SourceType.REVIEW_EXPORT.value:
                continue
            converted = _convert(
                claim.numeric_value or 0.0, claim.numeric_unit or "", comparable.statement.unit_key
            )
            if converted is None:
                continue
            if not values_differ(converted, comparable.statement.value):
                continue
            findings.append(
                FindingDraft(
                    finding_type=FindingType.REVIEW_SIGNAL.value,
                    severity=Severity.LOW.value,
                    title="Отзыв покупателя упоминает другое значение параметра",
                    description=(
                        "В отзыве указано: "
                        + _quote(claim.text)
                        + _value_note(
                            claim.text,
                            f"{claim.numeric_value:g} {unit_display(claim.numeric_unit or '')}",
                        )
                        + ".\n"
                        + "В описании товара: "
                        + _quote(comparable.text)
                        + _value_note(comparable.text, comparable.statement.describe())
                        + "."
                    ),
                    claim_id=comparable.claim_id,
                    evidence=[
                        EvidenceRef(
                            source_id=claim.source_id,
                            source_name=_source_name(claim),
                            excerpt=claim.text,
                            relation="uncertain",
                            evidence_type="review_statement",
                        ),
                        EvidenceRef(
                            source_id=comparable.source_id,
                            source_name=comparable.source_name,
                            excerpt=comparable.text,
                            relation="uncertain",
                        ),
                    ],
                    limitations=(
                        "Значение из отзыва может относиться к другой партии, "
                        "условиям использования или к измерению покупателем. "
                        "Отзыв не является доказательством: это пользовательский сигнал, "
                        "который требует проверки по первоисточникам."
                    ),
                    recommended_action=(
                        "Проверить, какое значение подтверждается документами, "
                        "и при необходимости уточнить описание."
                    ),
                    confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                    rule_id="reviews.numeric_mismatch",
                )
            )
            break

    return findings


def build_document_scope_findings(sources: Iterable, product_attributes: Dict) -> List[FindingDraft]:
    """Ищет документы, которые могут относиться к другой модели или версии."""
    findings: List[FindingDraft] = []
    product_model = ""
    for key, value in (product_attributes or {}).items():
        if "model" in key.lower() or "артикул" in key.lower():
            product_model = str(value)
            break

    for source in sources:
        if source.source_type not in {
            SourceType.TECHNICAL_DOCUMENT.value,
            SourceType.REVIEW_EXPORT.value,
        }:
            continue
        metadata = source.metadata_json or {}
        applies_to = str(metadata.get("applies_to_model") or "").strip()
        if applies_to and product_model and applies_to.lower() != product_model.lower():
            findings.append(
                FindingDraft(
                    finding_type=FindingType.DOCUMENT_SCOPE_MISMATCH.value,
                    severity=Severity.MEDIUM.value,
                    title="Документ может относиться к другой модели товара",
                    description=(
                        f"Источник «{source.source_name}» указывает область применения "
                        f"«{applies_to}», а в характеристиках товара указана модель "
                        f"«{product_model}».\n"
                        "Совпадение не подтверждено: документ может относиться к другой "
                        "модификации, партии или версии."
                    ),
                    claim_id=None,
                    evidence=[
                        EvidenceRef(
                            source_id=source.id,
                            source_name=source.source_name,
                            excerpt=f"Область применения: {applies_to}",
                            relation="uncertain",
                            evidence_type="document_statement",
                        )
                    ],
                    limitations=(
                        "Область применимости документа не проверялась по внешнему "
                        "государственному реестру — только по указанным вами данным."
                    ),
                    recommended_action=(
                        "Уточнить, к какой модели относится документ, и при необходимости "
                        "запросить документ на конкретную модификацию."
                    ),
                    confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                    rule_id="documents.scope_mismatch",
                )
            )

        valid_until = metadata.get("valid_until")
        if valid_until:
            findings.append(
                FindingDraft(
                    finding_type=FindingType.NEEDS_HUMAN_REVIEW.value,
                    severity=Severity.LOW.value,
                    title="Требуется проверить срок действия документа",
                    description=(
                        f"В источнике «{source.source_name}» указан срок действия до "
                        f"{valid_until}. Если документ уже недействителен, подтверждения "
                        "из него нужно трактовать с осторожностью."
                    ),
                    claim_id=None,
                    evidence=[
                        EvidenceRef(
                            source_id=source.id,
                            source_name=source.source_name,
                            excerpt=f"Действует до: {valid_until}",
                            relation="contextualizes",
                            evidence_type="document_statement",
                        )
                    ],
                    limitations=(
                        "Реальная дата окончания действия документа не проверялась "
                        "по официальным источникам."
                    ),
                    recommended_action=(
                        "Проверить актуальность документа и при необходимости "
                        "запросить действующую версию."
                    ),
                    confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
                    rule_id="documents.expired_or_soon",
                )
            )

    return findings


def build_unclassified_findings(claims: Iterable, relevant_source_types: Optional[set] = None) -> List[FindingDraft]:
    """Собирает утверждения, которые не удалось классифицировать.

    По умолчанию берутся только утверждения продавца (описание товара и
    заметки): неразобранные фразы в приложенных документах не создают
    шума, но остаются доступными в списке утверждений.
    """
    unclassified = [
        claim
        for claim in claims
        if claim.claim_type == "other" and not claim.user_confirmed and not claim.is_rejected
    ]
    if relevant_source_types is not None:
        unclassified = [
            claim
            for claim in unclassified
            if getattr(getattr(claim, "source", None), "source_type", None)
            in relevant_source_types
        ]
    if not unclassified:
        return []
    excerpts = "\n".join(f"— {_quote(claim.text)}" for claim in unclassified[:10])
    return [
        FindingDraft(
            finding_type=FindingType.NEEDS_HUMAN_REVIEW.value,
            severity=Severity.LOW.value,
            title="Часть утверждений требует ручной классификации",
            description=(
                f"Автоматически не удалось определить тип следующих утверждений "
                f"({len(unclassified)} шт.):\n{excerpts}"
            ),
            claim_id=unclassified[0].id,
            evidence=[
                EvidenceRef(
                    source_id=claim.source_id,
                    source_name=_source_name(claim),
                    excerpt=claim.text,
                    relation="contextualizes",
                )
                for claim in unclassified[:10]
            ],
            limitations=(
                "Это техническое ограничение разбора текста, а не признак проблемы "
                "с товаром."
            ),
            recommended_action=(
                "Откройте список утверждений и укажите тип вручную — проверка "
                "пересчитает находки."
            ),
            confidence_status=ConfidenceStatus.NEEDS_REVIEW.value,
            rule_id="claims.unclassified",
        )
    ]
