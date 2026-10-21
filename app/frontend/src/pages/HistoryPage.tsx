import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ReviewAction } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from '../components/States'
import { STATUS_LABELS, formatDate } from '../components/labels'

export function HistoryPage() {
  const [actions, setActions] = useState<ReviewAction[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setActions(await api.workspaceHistory(200))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить историю')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <>
      <header className="topbar">
        <div>
          <h1>История решений</h1>
          <div className="topbar-subtitle">
            Кто, когда и как изменил статус рассмотрения находок
          </div>
        </div>
        <button type="button" className="btn" onClick={() => void load()}>
          Обновить
        </button>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load()} />}

        {!actions && !error && (
          <div className="card">
            <Skeleton rows={5} />
          </div>
        )}

        {actions && actions.length === 0 && (
          <EmptyState
            title="Решений пока нет"
            description="История появится после того, как вы измените статус у находки или добавите комментарий."
            action={
              <Link className="btn btn-primary" to="/products">
                К товарам
              </Link>
            }
          />
        )}

        {actions && actions.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Пользователь</th>
                  <th>Действие</th>
                  <th>Переход статуса</th>
                  <th>Комментарий</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {actions.map((action) => (
                  <tr key={action.id}>
                    <td className="muted">{formatDate(action.created_at)}</td>
                    <td className="muted">{action.user_email}</td>
                    <td>
                      <span className="badge">
                        {action.action === 'status_change'
                          ? 'Смена статуса'
                          : 'Комментарий'}
                      </span>
                    </td>
                    <td className="muted">
                      {action.previous_status
                        ? `${STATUS_LABELS[action.previous_status as keyof typeof STATUS_LABELS] ?? action.previous_status} → ${STATUS_LABELS[action.new_status as keyof typeof STATUS_LABELS] ?? action.new_status}`
                        : '—'}
                    </td>
                    <td>{action.comment || '—'}</td>
                    <td>
                      <div className="table-actions">
                        <Link className="btn btn-sm" to={`/products/${action.product_id}`}>
                          К товару
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
