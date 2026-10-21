import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { AnalysisRun, Product } from '../api/types'
import { ClaimsTab } from '../components/ClaimsTab'
import { EvidenceTab } from '../components/EvidenceTab'
import { FindingsTab } from '../components/FindingsTab'
import { SourcesTab } from '../components/SourcesTab'
import { EmptyState, ErrorMessage, Loading } from '../components/States'
import { formatDate } from '../components/labels'

type TabKey = 'overview' | 'sources' | 'claims' | 'findings' | 'evidence' | 'runs'

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'overview', label: 'Карточка' },
  { key: 'sources', label: 'Источники' },
  { key: 'claims', label: 'Утверждения' },
  { key: 'findings', label: 'Находки' },
  { key: 'evidence', label: 'Доказательства' },
  { key: 'runs', label: 'Запуски' },
]

export function ProductPage() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [runs, setRuns] = useState<AnalysisRun[]>([])
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabKey>('overview')
  const [running, setRunning] = useState(false)
  const [runMessage, setRunMessage] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [loadedProduct, loadedRuns] = await Promise.all([
        api.getProduct(productId),
        api.listRuns(productId),
      ])
      setProduct(loadedProduct)
      setRuns(loadedRuns)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить товар')
    }
  }, [productId])

  useEffect(() => {
    void load()
  }, [load])

  async function runAnalysis() {
    setRunning(true)
    setError(null)
    setRunMessage(null)
    try {
      const run = await api.runAnalysis(productId)
      setRunMessage(
        `Проверка завершена: найдено находок — ${String(run.summary?.findings_total ?? 0)}.`,
      )
      setReloadKey((value) => value + 1)
      await load()
      setTab('findings')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить проверку')
    } finally {
      setRunning(false)
    }
  }

  if (error && !product) {
    return (
      <div className="content">
        <ErrorMessage message={error} onRetry={() => void load()} />
        <Link className="btn" to="/products">
          К списку товаров
        </Link>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="content">
        <Loading label="Загружаем товар…" />
      </div>
    )
  }

  const lastRun = runs[0]

  return (
    <>
      <header className="topbar">
        <div>
          <h1>{product.name}</h1>
          <div className="topbar-subtitle">
            {product.category || 'Категория не указана'} ·{' '}
            {product.marketplace === 'wildberries'
              ? 'Wildberries'
              : product.marketplace === 'ozon'
                ? 'Ozon'
                : product.marketplace === 'demo'
                  ? 'Демо'
                  : 'Другой маркетплейс'}
            {product.sku ? ` · ${product.sku}` : ''}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Link className="btn" to={`/products/${product.id}/edit`}>
            Редактировать
          </Link>
          <button type="button" className="btn btn-primary" onClick={() => void runAnalysis()} disabled={running}>
            {running ? 'Проверяем…' : 'Проверить карточку'}
          </button>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} />}
        {runMessage && <div className="alert alert-success">{runMessage}</div>}
        {product.is_demo && (
          <div className="alert alert-warning">
            Это демонстрационный товар: все описания, документы и отзывы синтетические и не
            относятся к реальным товарам.
          </div>
        )}

        <nav className="tabs" aria-label="Разделы товара">
          {TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={tab === item.key ? 'tab active' : 'tab'}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {tab === 'overview' && (
          <div className="grid grid-2">
            <div className="card">
              <div className="card-header">
                <h2>Описание товара</h2>
              </div>
              <div style={{ whiteSpace: 'pre-wrap' }}>
                {product.description || <span className="muted">Описание не заполнено.</span>}
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h2>Характеристики</h2>
              </div>
              {Object.keys(product.attributes ?? {}).length === 0 ? (
                <p className="muted">Характеристики не заданы.</p>
              ) : (
                <dl className="kv-list">
                  {Object.entries(product.attributes ?? {}).map(([key, value]) => (
                    <div key={key} style={{ display: 'contents' }}>
                      <dt className="mono">{key}</dt>
                      <dd>{String(value)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>

            <div className="card">
              <div className="card-header">
                <h2>Состояние проверки</h2>
              </div>
              {lastRun ? (
                <dl className="kv-list">
                  <dt>Последний запуск</dt>
                  <dd>{formatDate(lastRun.finished_at ?? lastRun.created_at)}</dd>
                  <dt>Статус</dt>
                  <dd>{lastRun.status}</dd>
                  <dt>Версия правил</dt>
                  <dd>{lastRun.rules_version}</dd>
                  <dt>Провайдер</dt>
                  <dd>
                    {lastRun.provider_name} {lastRun.provider_status ? `— ${lastRun.provider_status}` : ''}
                  </dd>
                  <dt>Находок</dt>
                  <dd>{String(lastRun.summary?.findings_total ?? 0)}</dd>
                </dl>
              ) : (
                <EmptyState
                  title="Проверка ещё не запускалась"
                  description="Добавьте источники и запустите проверку, чтобы увидеть найденные расхождения."
                  action={
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => void runAnalysis()}
                      disabled={running}
                    >
                      Запустить проверку
                    </button>
                  }
                />
              )}
            </div>

            <div className="card">
              <div className="card-header">
                <h2>Ограничения анализа</h2>
              </div>
              {lastRun?.limitations?.length ? (
                <ul>
                  {lastRun.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted">
                  Ограничения появятся после первого запуска проверки. Проверка всегда выполняется
                  только по предоставленным материалам.
                </p>
              )}
            </div>
          </div>
        )}

        {tab === 'sources' && <SourcesTab productId={product.id} />}
        {tab === 'claims' && <ClaimsTab productId={product.id} reloadKey={reloadKey} />}
        {tab === 'findings' && <FindingsTab productId={product.id} reloadKey={reloadKey} />}
        {tab === 'evidence' && <EvidenceTab productId={product.id} reloadKey={reloadKey} />}

        {tab === 'runs' && (
          <div className="card">
            <div className="card-header">
              <div>
                <h2>Запуски проверки ({runs.length})</h2>
                <p>Каждый запуск сохраняет версию правил, провайдера и сводку результата.</p>
              </div>
            </div>
            {runs.length === 0 ? (
              <EmptyState
                title="Запусков пока нет"
                description="Запустите проверку кнопкой «Проверить карточку»."
              />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Статус</th>
                      <th>Правила</th>
                      <th>Провайдер</th>
                      <th>Утверждений</th>
                      <th>Находок</th>
                      <th>Отчёт</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((run) => (
                      <tr key={run.id}>
                        <td className="muted">{formatDate(run.created_at)}</td>
                        <td>
                          <span className="badge badge-accent">{run.status}</span>
                        </td>
                        <td className="muted">{run.rules_version}</td>
                        <td className="muted">{run.provider_name}</td>
                        <td>{String(run.summary?.claims_total ?? 0)}</td>
                        <td>{String(run.summary?.findings_total ?? 0)}</td>
                        <td>
                          <Link className="btn btn-sm" to={`/products/${product.id}/report/${run.id}`}>
                            Открыть
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
