import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Evidence } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from './States'
import { RELATION_LABELS, formatDate } from './labels'

interface EvidenceTabProps {
  productId: string
  reloadKey: number
}

export function EvidenceTab({ productId, reloadKey }: EvidenceTabProps) {
  const [evidence, setEvidence] = useState<Evidence[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setEvidence(await api.listEvidence(productId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить доказательства')
    }
  }, [productId])

  useEffect(() => {
    void load()
  }, [load, reloadKey])

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Доказательства ({evidence?.length ?? 0})</h2>
          <p>Фрагменты источников, на которые опираются утверждения и находки.</p>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {!evidence && <Skeleton rows={4} />}

      {evidence && evidence.length === 0 && (
        <EmptyState
          title="Доказательств пока нет"
          description="Запустите проверку: система сохранит фрагменты источников вместе с утверждениями."
        />
      )}

      {evidence && evidence.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Фрагмент</th>
                <th>Источник</th>
                <th>Отношение</th>
                <th>Тип</th>
                <th>Дата</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className="excerpt">{item.excerpt}</div>
                    {item.relevance_note && (
                      <div className="small muted">{item.relevance_note}</div>
                    )}
                  </td>
                  <td className="muted">{item.source_name ?? '—'}</td>
                  <td>
                    <span
                      className={`badge ${
                        item.relation === 'supports'
                          ? 'badge-success'
                          : item.relation === 'contradicts'
                            ? 'badge-high'
                            : 'badge-info'
                      }`}
                    >
                      {RELATION_LABELS[item.relation] ?? item.relation}
                    </span>
                  </td>
                  <td className="muted">{item.evidence_type}</td>
                  <td className="muted">{formatDate(item.date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
