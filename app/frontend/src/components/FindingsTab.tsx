import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { Finding, FindingStatus, FindingType, Severity } from '../api/types'
import { FindingCard } from './FindingCard'
import { EmptyState, ErrorMessage, Skeleton } from './States'
import { FINDING_TYPE_LABELS, SEVERITY_LABELS, STATUS_LABELS } from './labels'

interface FindingsTabProps {
  productId: string
  reloadKey: number
}

export function FindingsTab({ productId, reloadKey }: FindingsTabProps) {
  const [findings, setFindings] = useState<Finding[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [includeArchived, setIncludeArchived] = useState(false)

  const params = useMemo(() => {
    const result: Record<string, string> = {}
    if (statusFilter) result.status = statusFilter
    if (typeFilter) result.type = typeFilter
    if (severityFilter) result.severity = severityFilter
    if (includeArchived) result.include_archived = 'true'
    return result
  }, [statusFilter, typeFilter, severityFilter, includeArchived])

  const load = useCallback(async () => {
    setError(null)
    try {
      setFindings(await api.listFindings(productId, params))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить находки')
    }
  }, [productId, params])

  useEffect(() => {
    void load()
  }, [load, reloadKey])

  const counts = useMemo(() => {
    const result: Record<string, number> = {}
    ;(findings ?? []).forEach((finding) => {
      result[finding.finding_type] = (result[finding.finding_type] ?? 0) + 1
    })
    return result
  }, [findings])

  return (
    <div className="stack">
      {error && <ErrorMessage message={error} onRetry={() => void load()} />}

      <div className="card">
        <div className="card-header">
          <div>
            <h2>Находки ({findings?.length ?? 0})</h2>
            <p>
              Каждая находка показывает, что найдено, на основании чего, чего не хватает и что
              делать дальше.
            </p>
          </div>
        </div>

        <div className="toolbar">
          <div className="field">
            <label htmlFor="filter-status" className="small">
              Статус
            </label>
            <select
              id="filter-status"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="">Все статусы</option>
              {(Object.keys(STATUS_LABELS) as FindingStatus[]).map((status) => (
                <option key={status} value={status}>
                  {STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-type" className="small">
              Тип находки
            </label>
            <select
              id="filter-type"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
            >
              <option value="">Все типы</option>
              {(Object.keys(FINDING_TYPE_LABELS) as FindingType[]).map((type) => (
                <option key={type} value={type}>
                  {FINDING_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-severity" className="small">
              Серьёзность
            </label>
            <select
              id="filter-severity"
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value)}
            >
              <option value="">Любая</option>
              {(Object.keys(SEVERITY_LABELS) as Severity[]).map((severity) => (
                <option key={severity} value={severity}>
                  {SEVERITY_LABELS[severity]}
                </option>
              ))}
            </select>
          </div>
          <label className="small" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(event) => setIncludeArchived(event.target.checked)}
              style={{ width: 'auto' }}
            />
            Показать архивные
          </label>
        </div>

        {!findings && <Skeleton rows={4} />}

        {findings && findings.length === 0 && (
          <EmptyState
            title="Находок нет"
            description="Либо проверка ещё не запускалась, либо в предоставленных материалах расхождений не обнаружено. Запустите проверку после загрузки источников."
          />
        )}

        {findings && findings.length > 0 && (
          <>
            <div className="chip-row" style={{ marginBottom: 14 }}>
              {Object.entries(counts).map(([type, count]) => (
                <span className="badge badge-accent" key={type}>
                  {FINDING_TYPE_LABELS[type as FindingType] ?? type}: {count}
                </span>
              ))}
            </div>
            {findings.map((finding) => (
              <FindingCard
                key={finding.id}
                finding={finding}
                onUpdated={() => void load()}
              />
            ))}
          </>
        )}
      </div>
    </div>
  )
}
