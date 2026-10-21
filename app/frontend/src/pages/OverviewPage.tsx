import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { OverviewStats } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from '../components/States'
import {
  FINDING_TYPE_LABELS,
  SEVERITY_LABELS,
  STATUS_LABELS,
  formatDate,
} from '../components/labels'
import { useAuth } from '../context/AuthContext'

export function OverviewPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<OverviewStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState(false)

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
    try {
      await api.seedDemo()
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать демо-товар')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Обзор</h1>
          <div className="topbar-subtitle">
            {user?.workspace?.name} · проверки выполняются только по предоставленным материалам
          </div>
        </div>
        <Link className="btn btn-primary" to="/products/new">
          + Создать товар
        </Link>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}

        {!stats && !error && (
          <div className="card">
            <Skeleton rows={4} />
          </div>
        )}

        {stats && (
          <>
            <div className="alert alert-info">
              Автоматический анализ помогает выявлять возможные несоответствия и не является
              юридическим заключением или независимым испытанием товара. Решения по спорным
              случаям всегда остаются за человеком.
            </div>

            <div className="grid grid-4">
              <div className="stat">
                <div className="stat-label">Товаров</div>
                <div className="stat-value">{stats.products_total}</div>
                <div className="stat-hint">в рабочем пространстве</div>
              </div>
              <div className="stat">
                <div className="stat-label">Открытых находок</div>
                <div className="stat-value">{stats.findings_open}</div>
                <div className="stat-hint">из {stats.findings_total} всего</div>
              </div>
              <div className="stat">
                <div className="stat-label">Источников</div>
                <div className="stat-value">{stats.sources_total}</div>
                <div className="stat-hint">включая отзывы: {stats.reviews_total}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Проверок</div>
                <div className="stat-value">{stats.runs_total}</div>
                <div className="stat-hint">запусков анализа</div>
              </div>
            </div>

            <div className="grid grid-2" style={{ marginTop: 16 }}>
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>Находки по типам</h2>
                    <p>Что именно обнаружила проверка</p>
                  </div>
                </div>
                {Object.keys(stats.findings_by_type).length === 0 ? (
                  <EmptyState
                    title="Находок пока нет"
                    description="Создайте товар, добавьте описание, характеристики и источники, затем запустите проверку."
                    action={
                      <Link className="btn btn-primary" to="/products/new">
                        Создать товар
                      </Link>
                    }
                  />
                ) : (
                  <div className="chip-row">
                    {Object.entries(stats.findings_by_type).map(([type, count]) => (
                      <span className="badge badge-accent" key={type}>
                        {FINDING_TYPE_LABELS[type as keyof typeof FINDING_TYPE_LABELS] ?? type}: {count}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>Находки по серьёзности и статусу</h2>
                    <p>Цвет — дополнительный сигнал, решение принимает человек</p>
                  </div>
                </div>
                <div className="chip-row" style={{ marginBottom: 10 }}>
                  {Object.entries(stats.findings_by_severity).map(([severity, count]) => (
                    <span className={`badge badge-${severity}`} key={severity}>
                      {SEVERITY_LABELS[severity as keyof typeof SEVERITY_LABELS] ?? severity}: {count}
                    </span>
                  ))}
                </div>
                <div className="chip-row">
                  {Object.entries(stats.findings_by_status).map(([status, count]) => (
                    <span className="badge" key={status}>
                      {STATUS_LABELS[status as keyof typeof STATUS_LABELS] ?? status}: {count}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <div>
                  <h2>Последние проверки</h2>
                  <p>История запусков анализа по вашим товарам</p>
                </div>
                <Link className="btn btn-sm" to="/checks">
                  Все проверки
                </Link>
              </div>
              {stats.recent_runs.length === 0 ? (
                <EmptyState
                  title="Проверок ещё не было"
                  description="Запустите проверку товара, чтобы увидеть найденные расхождения и их основания."
                />
              ) : (
                <div className="table-wrap">
                  <table>
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
                          <td>
                            <Link to={`/products/${run.product_id}`}>
                              {String(run.summary?.product_name ?? run.product_id).slice(0, 60)}
                            </Link>
                          </td>
                          <td className="muted">{formatDate(run.created_at)}</td>
                          <td>
                            <span className="badge badge-accent">{run.status}</span>
                          </td>
                          <td className="muted">{run.rules_version}</td>
                          <td className="muted">{run.provider_name}</td>
                          <td className="text-right">{String(run.summary?.findings_total ?? 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {stats.demo_products === 0 && (
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>Демонстрационный пример</h2>
                    <p>
                      Синтетический товар с явно помеченными данными: показывает работу всех типов
                      находок без доступа к реальным карточкам.
                    </p>
                  </div>
                </div>
                <button type="button" className="btn btn-primary" onClick={() => void seedDemo()} disabled={seeding}>
                  {seeding ? 'Создаём…' : 'Добавить демо-товар'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
