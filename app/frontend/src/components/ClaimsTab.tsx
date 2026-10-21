import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Claim } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from './States'
import { CLAIM_TYPE_LABELS, CONFIDENCE_LABELS, formatDate } from './labels'

interface ClaimsTabProps {
  productId: string
  reloadKey: number
}

const CLAIM_TYPES = Object.keys(CLAIM_TYPE_LABELS)

export function ClaimsTab({ productId, reloadKey }: ClaimsTabProps) {
  const [claims, setClaims] = useState<Claim[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setClaims(await api.listClaims(productId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить утверждения')
    }
  }, [productId])

  useEffect(() => {
    void load()
  }, [load, reloadKey])

  async function update(claim: Claim, payload: Parameters<typeof api.updateClaim>[1]) {
    try {
      await api.updateClaim(claim.id, payload)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить утверждение')
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>Утверждения ({claims?.length ?? 0})</h2>
          <p>
            Кандидаты извлекаются из описания и источников. Тип можно уточнить вручную —
            проверка пересчитает находки.
          </p>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {!claims && <Skeleton rows={5} />}

      {claims && claims.length === 0 && (
        <EmptyState
          title="Утверждения не найдены"
          description="Запустите проверку товара — система извлечёт утверждения из описания и источников."
        />
      )}

      {claims && claims.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Текст утверждения</th>
                <th>Тип</th>
                <th>Источник</th>
                <th>Значение</th>
                <th>Оценка</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.id} style={claim.is_rejected ? { opacity: 0.55 } : undefined}>
                  <td>
                    {claim.text}
                    {claim.user_confirmed && (
                      <span className="badge badge-success" style={{ marginLeft: 8 }}>
                        подтверждено
                      </span>
                    )}
                    {claim.is_rejected && (
                      <span className="badge" style={{ marginLeft: 8 }}>
                        отклонено
                      </span>
                    )}
                    <div className="small muted">{formatDate(claim.created_at)}</div>
                  </td>
                  <td>
                    <select
                      aria-label={`Тип утверждения: ${claim.text.slice(0, 40)}`}
                      value={claim.claim_type}
                      onChange={(event) => void update(claim, { claim_type: event.target.value })}
                      style={{ minWidth: 170 }}
                    >
                      {CLAIM_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {CLAIM_TYPE_LABELS[type]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="muted">{claim.source_name ?? 'Ручной ввод'}</td>
                  <td className="muted">
                    {claim.numeric_value !== null
                      ? `${claim.numeric_value} ${claim.numeric_unit ?? ''} (${claim.numeric_dimension ?? ''})`
                      : '—'}
                  </td>
                  <td className="muted small">
                    {CONFIDENCE_LABELS[claim.confidence_status] ?? claim.confidence_status}
                  </td>
                  <td>
                    <div className="table-actions">
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() =>
                          void update(claim, { user_confirmed: !claim.user_confirmed })
                        }
                      >
                        {claim.user_confirmed ? 'Снять подтверждение' : 'Подтвердить'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => void update(claim, { is_rejected: !claim.is_rejected })}
                      >
                        {claim.is_rejected ? 'Вернуть' : 'Отклонить'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
