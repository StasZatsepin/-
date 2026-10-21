import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { Finding, FindingStatus, FindingType, Severity } from '../api/types'
import { FindingCard } from './FindingCard'
import { EmptyState, ErrorMessage, Skeleton } from './States'
import {
  FINDING_TYPE_LABELS,
  FINDING_TYPE_META,
  SEVERITY_LABELS,
  STATUS_LABELS,
  formatCount,
} from './labels'
import { IconFilter, IconInfo } from './icons'

interface FindingsTabProps {
  productId: string
  reloadKey: number
}

/**
 * Список результатов проверки с фильтрами.
 *
 * Фильтры по типу и серьёзности помогают отделить доказанные расхождения от слабых
 * сигналов и неопределённости — поэтому они вынесены в отдельный блок.
 */
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
      setError(err instanceof Error ? err.message : 'Не удалось загрузить результаты')
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

  const hasFilters = Boolean(statusFilter || typeFilter || severityFilter || includeArchived)

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Результаты проверки ({formatCount(findings?.length ?? 0, ['результат', 'результата', 'результатов'])})</h2>
          <p>
            Каждый результат отвечает на четыре вопроса: что найдено, на основании чего, чего не
            хватает и что делать дальше.
          </p>
        </div>
      </div>

      <div className="panel-body" style={{ paddingBottom: 0 }}>
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}

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
              Тип сигнала
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
          <label className="checkbox">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(event) => setIncludeArchived(event.target.checked)}
            />
            Показать архивные
          </label>
          {hasFilters && (
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              onClick={() => {
                setStatusFilter('')
                setTypeFilter('')
                setSeverityFilter('')
                setIncludeArchived(false)
              }}
            >
              <IconFilter size={14} />
              Сбросить фильтры
            </button>
          )}
        </div>

        {findings && findings.length > 0 && (
          <div className="chip-row" style={{ marginBottom: 'var(--sp-4)' }}>
            {Object.entries(counts).map(([type, count]) => {
              const meta = FINDING_TYPE_META[type as FindingType]
              const Icon = meta?.icon
              return (
                <span className={`badge ${meta?.badge ?? 'badge-neutral'}`} key={type}>
                  {Icon && <Icon size={13} />}
                  {FINDING_TYPE_LABELS[type as FindingType] ?? type}: {count}
                </span>
              )
            })}
          </div>
        )}
      </div>

      <div className="panel-body">
        {!findings && <Skeleton rows={4} />}

        {findings && findings.length === 0 && (
          <EmptyState
            title={hasFilters ? 'Под фильтры ничего не подходит' : 'Результатов нет'}
            description={
              hasFilters
                ? 'Измените условия фильтрации или сбросьте их, чтобы увидеть все результаты проверки.'
                : 'Либо проверка ещё не запускалась, либо в предоставленных материалах расхождений не обнаружено.'
            }
            icon={<IconInfo size={22} />}
          />
        )}

        {findings && findings.length > 0 && (
          <div>
            {findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} onUpdated={() => void load()} />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
