import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AnalysisRun } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from '../components/States'
import { formatCount, formatDate } from '../components/labels'
import { IconChecks, IconPrint } from '../components/icons'

interface RunRow extends AnalysisRun {
  product_name: string
}

export function ChecksPage() {
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const products = await api.listProducts()
      const collected: RunRow[] = []
      for (const product of products) {
        const productRuns = await api.listRuns(product.id)
        productRuns.forEach((run) => collected.push({ ...run, product_name: product.name }))
      }
      collected.sort(
        (first, second) =>
          new Date(second.created_at).getTime() - new Date(first.created_at).getTime(),
      )
      setRuns(collected)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить проверки')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <>
      <header className="topbar">
        <div className="topbar-titles">
          <h1>Проверки</h1>
          <div className="topbar-subtitle">
            {runs
              ? formatCount(runs.length, ['запуск', 'запуска', 'запусков'])
              : 'Загрузка…'}
          </div>
        </div>
        <div className="topbar-actions">
          <button type="button" className="btn" onClick={() => void load()}>
            Обновить
          </button>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>История запусков</h2>
              <p>Каждый запуск сохраняет версию правил, провайдера и сводку результата</p>
            </div>
          </div>

          {!runs && !error && (
            <div className="panel-body">
              <Skeleton rows={5} />
            </div>
          )}

          {runs && runs.length === 0 && (
            <div className="panel-body">
              <EmptyState
                title="Проверок пока нет"
                description="Откройте товар и нажмите «Проверить карточку» — запуск появится здесь с указанием версии правил и ограничений."
                icon={<IconChecks size={22} />}
                action={
                  <Link className="btn btn-primary" to="/app/products">
                    К товарам
                  </Link>
                }
              />
            </div>
          )}

          {runs && runs.length > 0 && (
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Товар</th>
                    <th>Дата</th>
                    <th>Статус</th>
                    <th>Правила</th>
                    <th>Провайдер</th>
                    <th>Источников</th>
                    <th>Утверждений</th>
                    <th>Результатов</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>
                        <Link
                          to={`/app/products/${run.product_id}`}
                          className="cell-title"
                          style={{ color: 'var(--text)' }}
                        >
                          {run.product_name}
                        </Link>
                      </td>
                      <td className="muted">{formatDate(run.created_at)}</td>
                      <td>
                        <span className="badge badge-teal">{run.status}</span>
                      </td>
                      <td className="muted">{run.rules_version}</td>
                      <td className="muted">{run.provider_name}</td>
                      <td>{String(run.summary?.sources_total ?? 0)}</td>
                      <td>{String(run.summary?.claims_total ?? 0)}</td>
                      <td>{String(run.summary?.findings_total ?? 0)}</td>
                      <td>
                        <div className="table-actions">
                          <Link
                            className="btn btn-sm"
                            to={`/app/products/${run.product_id}/report/${run.id}`}
                          >
                            <IconPrint size={14} />
                            Отчёт
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </>
  )
}
