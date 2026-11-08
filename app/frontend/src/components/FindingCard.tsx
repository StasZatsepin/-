import { useState } from 'react'
import type { Finding, FindingStatus } from '../api/types'
import { api } from '../api/client'
import {
  FINDING_TYPE_LABELS,
  FINDING_TYPE_META,
  RELATION_BADGE,
  RULE_LABELS,
  labelOf,
  RELATION_LABELS,
  SEVERITY_BADGE,
  SEVERITY_LABELS,
  STATUS_BADGE,
  STATUS_LABELS,
} from './labels'
import { IconCheck, IconFile, IconInfo, IconQuote, IconScale, IconSpark } from './icons'

interface FindingCardProps {
  finding: Finding
  onUpdated?: (finding: Finding) => void
}

const STATUS_OPTIONS: FindingStatus[] = [
  'open',
  'in_review',
  'resolved',
  'not_an_issue',
  'insufficient_data',
]

/**
 * Карточка результата проверки — ключевой экран продукта.
 *
 * Показывает: что найдено, на основании чего, чего не хватает и что делать дальше.
 * Доказательства расходятся с утверждением не смешиваются: у каждого фрагмента
 * подписан источник и отношение к находке.
 */
export function FindingCard({ finding, onUpdated }: FindingCardProps) {
  const [status, setStatus] = useState<FindingStatus>(finding.status)
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const typeMeta = FINDING_TYPE_META[finding.finding_type]
  const TypeIcon = typeMeta.icon

  async function applyStatus(next: FindingStatus) {
    setSaving(true)
    setError(null)
    try {
      const updated = await api.updateFinding(finding.id, {
        status: next,
        comment: comment.trim() || undefined,
      })
      setStatus(updated.status)
      setComment('')
      onUpdated?.(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить статус')
    } finally {
      setSaving(false)
    }
  }

  async function saveComment() {
    if (!comment.trim()) return
    setSaving(true)
    setError(null)
    try {
      const updated = await api.updateFinding(finding.id, { comment: comment.trim() })
      setComment('')
      onUpdated?.(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить комментарий')
    } finally {
      setSaving(false)
    }
  }

  return (
    <article className={`finding sev-${finding.severity}`}>
      <div className="finding-body">
        <span className="finding-accent" aria-hidden="true" />

        <div className="finding-main">
          <div className="finding-head">
            <h3 className="finding-title">{finding.title}</h3>
            <span className={`badge ${STATUS_BADGE[status]}`}>{STATUS_LABELS[status]}</span>
          </div>

          <div className="finding-meta">
            <span className={`badge ${SEVERITY_BADGE[finding.severity]}`}>
              <span className="badge-dot" aria-hidden="true" />
              {SEVERITY_LABELS[finding.severity]}
            </span>
            <span className={`badge ${typeMeta.badge}`}>
              <TypeIcon size={13} />
              {FINDING_TYPE_LABELS[finding.finding_type]}
            </span>
            <span className="badge badge-neutral" title={`Идентификатор правила: ${finding.rule_id}, версия ${finding.rule_version}`}>
              {labelOf(RULE_LABELS, finding.rule_id, 'Автоматическая проверка')}
            </span>
          </div>

          <p className="finding-text">{finding.description}</p>

          {finding.source_refs.length > 0 && (
            <div className="finding-section">
              <div className="finding-section-label">
                <IconFile size={13} />
                Основание вывода
              </div>
              <div className="evidence-list">
                {finding.source_refs.map((ref, index) => (
                  <div className="evidence-item" key={`${ref.source_id ?? 'ref'}-${index}`}>
                    <span className="evidence-icon" aria-hidden="true">
                      {ref.evidence_type === 'review_statement' ? (
                        <IconQuote size={15} />
                      ) : ref.evidence_type === 'attribute_value' ? (
                        <IconScale size={15} />
                      ) : (
                        <IconFile size={15} />
                      )}
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <div className="evidence-source">
                        <span>{ref.source_name}</span>
                        <span className={`badge ${RELATION_BADGE[ref.relation] ?? 'badge-neutral'}`}>
                          {RELATION_LABELS[ref.relation] ?? ref.relation}
                        </span>
                      </div>
                      <div className="evidence-excerpt">{ref.excerpt}</div>
                      {ref.note && <div className="evidence-note">{ref.note}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {finding.limitations && (
            <div className="finding-section">
              <div className="callout callout-limit">
                <span className="callout-icon" aria-hidden="true">
                  <IconInfo size={16} />
                </span>
                <div>
                  <strong>Ограничение вывода</strong>
                  {finding.limitations}
                </div>
              </div>
            </div>
          )}

          {finding.explanation && (
            <div className="finding-section">
              <div className="callout callout-model">
                <span className="callout-icon" aria-hidden="true">
                  <IconSpark size={16} />
                </span>
                <div>
                  <strong>
                    Комментарий модели{finding.explanation_provider ? ` (${finding.explanation_provider})` : ''}
                  </strong>
                  {finding.explanation}
                  <div className="evidence-note">
                    Пояснение дополняет находку, но не меняет её тип и серьёзность: их
                    определяют детерминированные правила.
                  </div>
                </div>
              </div>
            </div>
          )}

          {finding.recommended_action && (
            <div className="finding-section">
              <div className="callout callout-action">
                <span className="callout-icon" aria-hidden="true">
                  <IconCheck size={16} />
                </span>
                <div>
                  <strong>Рекомендуемое действие</strong>
                  {finding.recommended_action}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="alert alert-error" style={{ margin: '0 var(--sp-5) var(--sp-4)' }}>
          <span className="alert-icon">
            <IconInfo size={16} />
          </span>
          <div>{error}</div>
        </div>
      )}

      <div className="finding-footer">
        <div className="field">
          <label htmlFor={`status-${finding.id}`}>Статус рассмотрения</label>
          <select
            id={`status-${finding.id}`}
            value={status}
            onChange={(event) => setStatus(event.target.value as FindingStatus)}
            disabled={saving}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {STATUS_LABELS[option]}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void applyStatus(status)}
          disabled={saving}
        >
          {saving ? 'Сохраняем…' : 'Сменить статус'}
        </button>

        <div className="field">
          <label htmlFor={`comment-${finding.id}`}>Комментарий решения</label>
          <input
            id={`comment-${finding.id}`}
            type="text"
            value={comment}
            placeholder="Например: запросили подтверждающий документ у поставщика"
            onChange={(event) => setComment(event.target.value)}
            disabled={saving}
          />
        </div>
        <button
          type="button"
          className="btn"
          onClick={() => void saveComment()}
          disabled={saving || !comment.trim()}
        >
          Добавить комментарий
        </button>
      </div>
    </article>
  )
}
