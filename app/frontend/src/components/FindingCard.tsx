import { useState } from 'react'
import type { Finding, FindingStatus } from '../api/types'
import { api } from '../api/client'
import {
  FINDING_TYPE_LABELS,
  SEVERITY_LABELS,
  STATUS_LABELS,
} from './labels'

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

export function FindingCard({ finding, onUpdated }: FindingCardProps) {
  const [status, setStatus] = useState<FindingStatus>(finding.status)
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    <article className={`finding severity-${finding.severity}`}>
      <div className="finding-head">
        <div>
          <div className="finding-title">{finding.title}</div>
          <div className="finding-meta">
            <span className={`badge badge-${finding.severity}`}>
              <span className="badge-dot" aria-hidden="true" />
              {SEVERITY_LABELS[finding.severity]}
            </span>
            <span className="badge">{FINDING_TYPE_LABELS[finding.finding_type]}</span>
            <span className={`badge ${status === 'resolved' ? 'badge-success' : 'badge-accent'}`}>
              {STATUS_LABELS[status]}
            </span>
            <span className="badge">правило {finding.rule_id || finding.origin}</span>
          </div>
        </div>
      </div>

      <div className="finding-body">{finding.description}</div>

      {finding.source_refs.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div className="small muted">Основание вывода:</div>
          {finding.source_refs.map((ref, index) => (
            <div className="excerpt" key={`${ref.source_id ?? 'ref'}-${index}`}>
              <span className="excerpt-source">
                {ref.source_name} · {ref.relation}
              </span>
              {ref.excerpt}
            </div>
          ))}
        </div>
      )}

      {finding.limitations && (
        <div className="note-block">
          <strong>Ограничение.</strong> {finding.limitations}
        </div>
      )}
      {finding.recommended_action && (
        <div className="note-block">
          <strong>Рекомендуемое действие.</strong> {finding.recommended_action}
        </div>
      )}

      {error && (
        <div className="alert alert-error" style={{ marginTop: 12, marginBottom: 0 }}>
          {error}
        </div>
      )}

      <div className="inline-form" style={{ marginTop: 14 }}>
        <div className="field" style={{ flex: 1, minWidth: 260 }}>
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
      </div>

      <div className="inline-form" style={{ marginTop: 10 }}>
        <div className="field" style={{ flex: 1, minWidth: 260 }}>
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
