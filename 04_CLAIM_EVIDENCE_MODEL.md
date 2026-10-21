# Модель утверждений и доказательств

## 1. Термины

-   Claim: утверждение, которое продавец сообщает покупателю.
-   Evidence: источник или фрагмент данных, относящийся к утверждению.
-   Finding: потенциальная проблема, выявленная правилом или анализом.
-   Source: документ, характеристика, текст описания или отзыв,
    загруженный пользователем.
-   ReviewAction: решение человека по finding.

## 2. Типы утверждений

-   `numeric_performance`: числовая производительность/длительность.
-   `dimension_or_weight`: размер, вес, габарит.
-   `compatibility`: совместимость с устройством/моделью.
-   `material_or_composition`: материал/состав.
-   `certification_or_compliance`: сертификация/соответствие.
-   `warranty_or_service`: гарантия/обслуживание.
-   `safety_or_health`: безопасность/эффект для здоровья --- повышенная
    осторожность.
-   `subjective_marketing`: «лучший», «профессиональный», «комфортный».
-   `other`.

## 3. Происхождение источника

Каждый source должен иметь: - `source_type`: product_description,
attribute_sheet, technical_document, review_export, user_note, other; -
`source_name`; - `uploaded_at`; - `source_date` (nullable); -
`source_uri` (nullable, только если предоставлен пользователем); -
`content_hash`; - `extraction_method`; - `extraction_status`; -
`workspace_id`, `product_id`.

## 4. Модель Claim

-   `id`
-   `product_id`
-   `text`
-   `claim_type`
-   `source_id`
-   `source_excerpt`
-   `start_offset` / `end_offset` (nullable)
-   `extraction_method`
-   `model_version` (nullable)
-   `confidence_label` (nullable; not a truth probability)
-   `user_confirmed`
-   `created_at`, `updated_at`

## 5. Модель Evidence

-   `id`
-   `product_id`
-   `source_id`
-   `evidence_type`
-   `excerpt`
-   `relation`: supports, contradicts, contextualizes, unrelated,
    uncertain
-   `relevance_note`
-   `date` (nullable)
-   `created_at`

## 6. Модель Finding

-   `id`
-   `product_id`
-   `claim_id` (nullable)
-   `finding_type`
-   `severity`: info, low, medium, high
-   `title`
-   `description`
-   `source_evidence_ids`
-   `limitations`
-   `recommended_action`
-   `status`
-   `rule_id` / `rule_version`
-   `analysis_run_id`
-   `created_at`, `updated_at`

## 7. Уровень уверенности

Не использовать единый «процент правдивости товара». В MVP допустимы
понятные статусы: - `supported_by_provided_source`: есть подходящий
источник, но это не обязательно независимое доказательство; -
`conflicting_sources`: обнаружены расходящиеся значения; -
`insufficient_evidence`: данных недостаточно; -
`subjective_or_not_testable`: утверждение не имеет заданного
объективного критерия; - `needs_human_review`: требуется проверка
человеком.

## 8. Правила интерпретации

-   Характеристика и обещание могут различаться из-за разных условий
    измерения; если условия неизвестны, не заявлять о прямом
    противоречии.
-   Отзыв --- субъективный опыт; показывать его как сигнал, не как
    установленный факт.
-   Несколько отзывов не считать независимыми без проверки уникальности
    и происхождения.
-   Документ может относиться к другой модели, партии или версии; при
    неопределённости создать `document_scope_mismatch` или
    `needs_human_review`.
-   Истечение срока документа считать проблемой только если срок
    известен и релевантен.
-   «Не найдено подтверждение» отличается от «утверждение ложное».
-   Сохранить исходный текст и ссылку на источник для каждого
    автоматического вывода.
