import type { ReactNode } from 'react'
import { FindingType, Severity, FindingStatus } from '../api/types'

export const FINDING_TYPE_LABELS: Record<FindingType, string> = {
  direct_conflict: 'Прямое расхождение',
  missing_evidence: 'Нет подтверждения',
  review_signal: 'Сигнал из отзывов',
  ambiguous_claim: 'Неоднозначное утверждение',
  document_scope_mismatch: 'Область применения документа',
  needs_human_review: 'Нужна проверка человека',
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  info: 'Информация',
  low: 'Низкая',
  medium: 'Средняя',
  high: 'Высокая',
}

export const STATUS_LABELS: Record<FindingStatus, string> = {
  open: 'Открыта',
  in_review: 'На рассмотрении',
  resolved: 'Решена',
  not_an_issue: 'Не проблема',
  insufficient_data: 'Недостаточно данных',
}

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  product_description: 'Описание товара',
  attribute_sheet: 'Таблица характеристик',
  technical_document: 'Технический документ',
  review_export: 'Отзывы',
  user_note: 'Заметка',
  other: 'Прочее',
}

export const CLAIM_TYPE_LABELS: Record<string, string> = {
  numeric_performance: 'Числовая характеристика',
  dimension_or_weight: 'Размер или вес',
  compatibility: 'Совместимость',
  material_or_composition: 'Материал или состав',
  certification_or_compliance: 'Сертификация',
  warranty_or_service: 'Гарантия и сервис',
  safety_or_health: 'Безопасность и здоровье',
  subjective_marketing: 'Оценочный маркетинг',
  other: 'Прочее',
}

export const CONFIDENCE_LABELS: Record<string, string> = {
  supported_by_provided_source: 'Есть подтверждение в предоставленных данных',
  conflicting_sources: 'Источники расходятся',
  insufficient_evidence: 'Недостаточно данных',
  subjective_or_not_testable: 'Нет объективного критерия',
  needs_human_review: 'Нужна проверка человеком',
}

export const RELATION_LABELS: Record<string, string> = {
  supports: 'подтверждает',
  contradicts: 'противоречит',
  contextualizes: 'контекст',
  unrelated: 'не связано',
  uncertain: 'неопределённо',
}

export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatBytes(value?: number | null): string {
  if (!value) return '—'
  if (value < 1024) return `${value} Б`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} КБ`
  return `${(value / (1024 * 1024)).toFixed(1)} МБ`
}

export function InfoBadge({ children }: { children: ReactNode }) {
  return <span className="badge badge-info">{children}</span>
}
