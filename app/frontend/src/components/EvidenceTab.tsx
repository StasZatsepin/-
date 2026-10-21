import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Evidence } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from './States'
import { RELATION_BADGE, RELATION_LABELS, formatDate , formatCount } from './labels'
import { IconFile, IconQuote, IconScale } from './icons'

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
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Доказательства ({formatCount(evidence?.length ?? 0, ['доказательство', 'доказательства', 'доказательств'])})</h2>
          <p>Фрагменты источников, на которые опираются утверждения и результаты проверки</p>
        </div>
      </div>

      {error && (
        <div className="panel-body" style={{ paddingBottom: 0 }}>
          <ErrorMessage message={error} />
        </div>
      )}

      {!evidence && (
        <div className="panel-body">
          <Skeleton rows={4} />
        </div>
      )}

      {evidence && evidence.length === 0 && (
        <div className="panel-body">
          <EmptyState
            title="Доказательств пока нет"
            description="Запустите проверку: система сохранит фрагменты источников вместе с утверждениями."
            icon={<IconFile size={22} />}
          />
        </div>
      )}

      {evidence && evidence.length > 0 && (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Фрагмент</th>
                <th>Источник</th>
                <th>Отношение</th>
                <th>Дата</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className="evidence-item" style={{ background: 'var(--surface-2)' }}>
                      <span className="evidence-icon" aria-hidden="true">
                        {item.evidence_type === 'review_statement' ? (
                          <IconQuote size={15} />
                        ) : item.evidence_type === 'attribute_value' ? (
                          <IconScale size={15} />
                        ) : (
                          <IconFile size={15} />
                        )}
                      </span>
                      <div style={{ minWidth: 0 }}>
                        <div className="evidence-excerpt">{item.excerpt}</div>
                        {item.relevance_note && (
                          <div className="evidence-note">{item.relevance_note}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="muted">{item.source_name ?? '—'}</td>
                  <td>
                    <span className={`badge ${RELATION_BADGE[item.relation] ?? 'badge-neutral'}`}>
                      {RELATION_LABELS[item.relation] ?? item.relation}
                    </span>
                  </td>
                  <td className="muted">{formatDate(item.date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
