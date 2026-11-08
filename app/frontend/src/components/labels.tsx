import type { FindingStatus, FindingType, Severity } from '../api/types'
import { IconConflict, IconFile, IconInfo, IconMissing, IconQuote, IconScope } from './icons'

export const FINDING_TYPE_LABELS: Record<FindingType, string> = {
  direct_conflict: 'Прямое расхождение',
  missing_evidence: 'Нет подтверждения',
  review_signal: 'Сигнал из отзывов',
  ambiguous_claim: 'Неоднозначное утверждение',
  document_scope_mismatch: 'Область применения документа',
  needs_human_review: 'Нужна проверка человеком',
}

/** Визуальный класс значка и иконка для каждого типа находки. */
export const FINDING_TYPE_META: Record<
  FindingType,
  { badge: string; icon: typeof IconConflict; description: string }
> = {
  direct_conflict: {
    badge: 'badge-danger',
    icon: IconConflict,
    description: 'Источники сообщают разные значения одного параметра',
  },
  missing_evidence: {
    badge: 'badge-info',
    icon: IconMissing,
    description: 'Проверяемое утверждение не подтверждено предоставленными материалами',
  },
  review_signal: {
    badge: 'badge-teal',
    icon: IconQuote,
    description: 'Пользовательский опыт, который стоит проверить',
  },
  ambiguous_claim: {
    badge: 'badge-violet',
    icon: IconInfo,
    description: 'Формулировку нельзя проверить объективно',
  },
  document_scope_mismatch: {
    badge: 'badge-warn',
    icon: IconScope,
    description: 'Документ может относиться к другой модели или версии',
  },
  needs_human_review: {
    badge: 'badge-warn',
    icon: IconFile,
    description: 'Данных недостаточно для автоматического вывода',
  },
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  info: 'Информация',
  low: 'Низкая',
  medium: 'Средняя',
  high: 'Высокая',
}

export const SEVERITY_BADGE: Record<Severity, string> = {
  info: 'badge-neutral',
  low: 'badge-info',
  medium: 'badge-warn',
  high: 'badge-danger',
}

export const STATUS_LABELS: Record<FindingStatus, string> = {
  open: 'Открыта',
  in_review: 'На рассмотрении',
  resolved: 'Решена',
  not_an_issue: 'Не проблема',
  insufficient_data: 'Недостаточно данных',
}

export const STATUS_BADGE: Record<FindingStatus, string> = {
  open: 'badge-neutral',
  in_review: 'badge-accent',
  resolved: 'badge-teal',
  not_an_issue: 'badge-neutral',
  insufficient_data: 'badge-warn',
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

export const RELATION_BADGE: Record<string, string> = {
  supports: 'badge-teal',
  contradicts: 'badge-danger',
  contextualizes: 'badge-info',
  unrelated: 'badge-neutral',
  uncertain: 'badge-neutral',
}

export const MARKETPLACE_LABELS: Record<string, string> = {
  ozon: 'Ozon',
  wildberries: 'Wildberries',
  demo: 'Демо',
  other: 'Другой',
}

export const RULE_LABELS: Record<string, string> = {
  'numeric.attribute_comparison': 'Сравнение описания с таблицей характеристик',
  'numeric.internal_consistency': 'Согласованность значений внутри источников',
  'claims.ambiguous_promise': 'Обещание без объективного критерия',
  'claims.unclassified': 'Тип утверждения не определён',
  'evidence.missing_safety_confirmation': 'Нет подтверждения заявления о безопасности',
  'evidence.missing_confirmation': 'Нет подтверждения в предоставленных материалах',
  'reviews.negative_signal': 'Негативный сигнал из отзывов',
  'reviews.mixed_signal': 'Отзывы расходятся во мнениях',
  'reviews.numeric_mismatch': 'Отзыв расходится с описанием по числу',
  'documents.scope_mismatch': 'Документ относится к другой модели или версии',
  'documents.expired_or_soon': 'Срок действия документа',
  'provider.suggestion': 'Предложение языковой модели',
}

export const RUN_STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает запуска',
  running: 'Выполняется',
  completed: 'Завершена',
  failed: 'Ошибка',
}

export const PROVIDER_LABELS: Record<string, string> = {
  mock: 'Встроенные правила',
  ollama: 'Ollama (локальная модель)',
  openai_compatible: 'OpenAI-совместимый сервис',
  openrouter: 'OpenRouter',
}

/** Подпись по ключу; сырой технический код пользователю не показываем. */
export function labelOf(map: Record<string, string>, key: string | null | undefined, fallback = 'Прочее'): string {
  if (!key) return fallback
  return map[key] ?? fallback
}

/**
 * Русское склонение числительных: plural(5, ['карточка', 'карточки', 'карточек']).
 */
export function plural(count: number, forms: [string, string, string]): string {
  const absolute = Math.abs(count) % 100
  const tail = absolute % 10
  if (absolute > 10 && absolute < 20) return forms[2]
  if (tail > 1 && tail < 5) return forms[1]
  if (tail === 1) return forms[0]
  return forms[2]
}

export function formatCount(count: number, forms: [string, string, string]): string {
  return `${count} ${plural(count, forms)}`
}

export function formatDate(value?: string | null, showTime = false): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const options: Intl.DateTimeFormatOptions = {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }
  if (showTime) {
    options.hour = '2-digit'
    options.minute = '2-digit'
  } else if (date.getHours() === 0 && date.getMinutes() === 0 && date.getSeconds() === 0) {
    // Пропускаем время, если оно ровно полночь — это бессмысленно
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } else {
    options.hour = '2-digit'
    options.minute = '2-digit'
  }
  return date.toLocaleString('ru-RU', options)
}

export function formatDateOnly(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function formatBytes(value?: number | null): string {
  if (!value) return '—'
  if (value < 1024) return `${value} Б`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} КБ`
  return `${(value / (1024 * 1024)).toFixed(1)} МБ`
}
