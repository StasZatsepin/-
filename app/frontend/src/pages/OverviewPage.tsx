import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { OverviewStats } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from '../components/States'
import { FINDING_TYPE_LABELS, FINDING_TYPE_META, SEVERITY_LABELS, STATUS_LABELS, formatDate, RUN_STATUS_LABELS, PROVIDER_LABELS, labelOf } from '../components/labels'
import {
  IconArrowRight,
  IconChecks,
  IconFile,
  IconPlus,
  IconProducts,
} from '../components/icons'
import { useAuth } from '../context/AuthContext'

const SEVERITY_COLORS: Record<string, string> = {
  high: 'var(--danger)',
  medium: 'var(--warn)',
  low: 'var(--info)',
  info: 'var(--text-3)',
}

export function OverviewPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<OverviewStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState(false)
  const [seedMessage, setSeedMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setStats(await api.overview())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить сводку')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function seedDemo() {
    setSeeding(true)
    setError(null)
    setSeedMessage(null)
    try {
      await api.seedDemo()
      setSeedMessage('Демонстрационный товар добавлен в рабочее пространство.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать демо-товар')
    } finally {
      setSeeding(false)
    }
  }

  const typeEntries = Object.entries(stats?.findings_by_type ?? {})
  const totalFindings = stats?.findings_total ?? 0

  return (
    <>
      <header className="topbar">
        <div className="topbar-titles">
          <h1>Обзор</h1>
          <div className="topbar-subtitle">
            {user?.workspace?.name} — проверки выполняются только по предоставленным материалам
          </div>
        </div>
        <div className="topbar-actions">
          <Link className="btn" to="/app/checks">
            <IconChecks size={16} />
            История проверок
          </Link>
          <Link className="btn btn-primary" to="/app/products/new">
            <IconPlus size={16} />
            Создать товар
          </Link>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}
        {seedMessage && <div className="alert alert-success">{seedMessage}</div>}

        {!stats && !error && (
          <div className="panel">
            <div className="panel-body">
              <Skeleton rows={5} />
            </div>
          </div>
        )}

        {stats && (
          <>
            <div className="alert alert-info">
              <span className="alert-icon" aria-hidden="true">
                <IconChecks size={16} />
              </span>
              <div>
                <strong>Что означают эти цифры</strong>
                Автоматический анализ помогает выявлять возможные несоответствия и не является
                юридическим заключением или независимым испытанием товара. Решения по спорным
                случаям всегда остаются за человеком.
              </div>
            </div>

            <div className="grid grid-4">
              <div className="metric">
                <div className="metric-label">
                  <span className="metric-icon">
                    <IconProducts size={16} />
                  </span>
                  Товаров
                </div>
                <div className="metric-value">{stats.products_total}</div>
                <div className="metric-hint">в рабочем пространстве</div>
              </div>
              <div className="metric">
                <div className="metric-label">
                  <span className="metric-icon" style={{ background: 'var(--warn-soft)', color: 'var(--warn)' }}>
                    <IconChecks size={16} />
                  </span>
                  К рассмотрению
                </div>
                <div className="metric-value">{stats.findings_open}</div>
                <div className="metric-hint">из {stats.findings_total} найденных результатов</div>
              </div>
              <div className="metric">
                <div className="metric-label">
                  <span className="metric-icon" style={{ background: 'var(--teal-soft)', color: 'var(--teal-700)' }}>
                    <IconFile size={16} />
                  </span>
                  Источников
                </div>
                <div className="metric-value">{stats.sources_total}</div>
                <div className="metric-hint">включая отзывы: {stats.reviews_total}</div>
              </div>
              <div className="metric">
                <div className="metric-label">
                  <span className="metric-icon" style={{ background: 'var(--violet-soft)', color: 'var(--violet)' }}>
                    <IconChecks size={16} />
                  </span>
                  Проверок
                </div>
                <div className="metric-value">{stats.runs_total}</div>
                <div className="metric-hint">запусков анализа</div>
              </div>
            </div>

            <div className="grid grid-2" style={{ marginTop: 'var(--sp-4)' }}>
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Что именно нашла проверка</h2>
                    <p>Распределение результатов по типам сигналов</p>
                  </div>
                </div>
                <div className="panel-body">
                  {typeEntries.length === 0 ? (
                    <EmptyState
                      title="Результатов пока нет"
                      description="Создайте товар, добавьте описание, характеристики и источники, затем запустите проверку."
                      action={
                        <Link className="btn btn-primary" to="/app/products/new">
                          Создать товар
                        </Link>
                      }
                    />
                  ) : (
                    <div className="distribution">
                      {typeEntries.map(([type, count]) => {
                        const meta =
                          FINDING_TYPE_META[type as keyof typeof FINDING_TYPE_META]
                        const percent = totalFindings ? Math.round((count / totalFindings) * 100) : 0
                        const Icon = meta?.icon
                        return (
                          <div className="distribution-row" key={type}>
                            <span className="chip-row">
                              {Icon && <Icon size={14} />}
                              {FINDING_TYPE_LABELS[type as keyof typeof FINDING_TYPE_LABELS] ?? type}
                            </span>
                            <span className="distribution-bar">
                              <span
                                style={{
                                  width: `${percent}%`,
                                  background: meta?.badge.replace('badge-', '') === 'danger'
                                    ? 'var(--danger)'
                                    : 'var(--accent)',
                                }}
                              />
                            </span>
                            <span className="muted">{count}</span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Серьёзность и статус</h2>
                    <p>Цвет — дополнительный сигнал, решение принимает человек</p>
                  </div>
                </div>
                <div className="panel-body">
                  <div className="distribution" style={{ marginBottom: 'var(--sp-5)' }}>
                    {Object.entries(stats.findings_by_severity).length === 0 && (
                      <p className="muted">Пока нет результатов.</p>
                    )}
                    {Object.entries(stats.findings_by_severity).map(([severity, count]) => (
                      <div className="distribution-row" key={severity}>
                        <span>{SEVERITY_LABELS[severity as keyof typeof SEVERITY_LABELS] ?? severity}</span>
                        <span className="distribution-bar">
                          <span
                            style={{
                              width: `${totalFindings ? Math.round((count / totalFindings) * 100) : 0}%`,
                              background: SEVERITY_COLORS[severity] ?? 'var(--accent)',
                            }}
                          />
                        </span>
                        <span className="muted">{count}</span>
                      </div>
                    ))}
                  </div>

                  <div className="chip-row">
                    {Object.entries(stats.findings_by_status).map(([status, count]) => (
                      <span className="badge badge-neutral" key={status}>
                        {STATUS_LABELS[status as keyof typeof STATUS_LABELS] ?? status}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              </section>
            </div>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Последние проверки</h2>
                  <p>История запусков анализа по вашим товарам</p>
                </div>
                <Link className="btn btn-sm" to="/app/checks">
                  Все проверки
                  <IconArrowRight size={15} />
                </Link>
              </div>

              {stats.recent_runs.length === 0 ? (
                <div className="panel-body">
                  <EmptyState
                    title="Проверок ещё не было"
                    description="Запустите проверку товара, чтобы увидеть найденные расхождения и их основания."
                    action={
                      <Link className="btn btn-primary" to="/app/products">
                        Перейти к товарам
                      </Link>
                    }
                  />
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="data stack">
                    <thead>
                      <tr>
                        <th>Товар</th>
                        <th>Дата</th>
                        <th>Статус</th>
                        <th>Правила</th>
                        <th>Провайдер</th>
                        <th className="text-right">Находок</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recent_runs.map((run) => (
                        <tr key={run.id}>
                          <td className="cell-main" data-label="Товар">
                            <Link
                              to={`/app/products/${run.product_id}`}
                              className="cell-title"
                              style={{ color: 'var(--text)' }}
                            >
                              {String(run.summary?.product_name ?? 'Товар')}
                            </Link>
                          </td>
                          <td className="muted" data-label="Дата">{formatDate(run.created_at)}</td>
                          <td data-label="Статус">
                            <span className="badge badge-teal">{labelOf(RUN_STATUS_LABELS, run.status)}</span>
                          </td>
                          <td className="muted" data-label="Правила">{run.rules_version}</td>
                          <td className="muted" data-label="Провайдер">{labelOf(PROVIDER_LABELS, run.provider_name)}</td>
                          <td className="text-right" data-label="Находок">{String(run.summary?.findings_total ?? 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {stats.demo_products === 0 && (
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h2>Демонстрационный пример</h2>
                    <p>
                      Синтетический товар с явно помеченными данными: показывает работу всех типов
                      результатов без доступа к реальным карточкам.
                    </p>
                  </div>
                </div>
                <div className="panel-body">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => void seedDemo()}
                    disabled={seeding}
                  >
                    <IconPlus size={16} />
                    {seeding ? 'Создаём…' : 'Добавить демо-товар'}
                  </button>
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </>
  )
}
