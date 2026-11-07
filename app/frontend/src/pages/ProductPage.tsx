import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { AnalysisRun, Product } from '../api/types'
import { ClaimsTab } from '../components/ClaimsTab'
import { EvidenceTab } from '../components/EvidenceTab'
import { FindingsTab } from '../components/FindingsTab'
import { SourcesTab } from '../components/SourcesTab'
import { EmptyState, ErrorMessage, Loading } from '../components/States'
import { MARKETPLACE_LABELS, formatDate } from '../components/labels'
import {
  IconChecks,
  IconEdit,
  IconFile,
  IconInfo,
  IconPrint,
  IconSpark,
} from '../components/icons'

type TabKey = 'overview' | 'sources' | 'claims' | 'findings' | 'evidence' | 'runs'

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'overview', label: 'Карточка' },
  { key: 'sources', label: 'Источники' },
  { key: 'claims', label: 'Утверждения' },
  { key: 'findings', label: 'Результаты' },
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
        `Проверка завершена: найдено результатов — ${String(run.summary?.findings_total ?? 0)}.`,
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
        <Link className="btn" to="/app/products">
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
  const lastSummary = lastRun?.summary ?? {}

  return (
    <>
      <header className="topbar">
        <div className="topbar-titles">
          <h1>{product.name}</h1>
          <div className="topbar-subtitle">
            {product.category || 'Категория не указана'}
            {product.marketplace && (
              <>
                , {MARKETPLACE_LABELS[product.marketplace] ?? product.marketplace}
              </>
            )}
            {product.sku ? `, артикул ${product.sku}` : ''}
          </div>
        </div>
        <div className="topbar-actions">
          <Link className="btn" to={`/app/products/${product.id}/edit`}>
            <IconEdit size={16} />
            Редактировать
          </Link>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void runAnalysis()}
            disabled={running}
          >
            <IconSpark size={16} />
            {running ? 'Проверяем…' : 'Проверить карточку'}
          </button>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} />}
        {runMessage && (
          <div className="alert alert-success">
            <span className="alert-icon">
              <IconChecks size={16} />
            </span>
            <div>{runMessage}</div>
          </div>
        )}
        {product.is_demo && (
          <div className="alert alert-warn">
            <span className="alert-icon">
              <IconInfo size={16} />
            </span>
            <div>
              <strong>Демонстрационный товар</strong>
              Все описания, документы и отзывы синтетические и не относятся к реальным товарам.
            </div>
          </div>
        )}

        {running && (
          <div className="panel" style={{ marginBottom: 'var(--sp-4)' }}>
            <div className="panel-body">
              <div className="flex-between" style={{ marginBottom: 12 }}>
                <strong>Идёт проверка</strong>
                <span className="muted small">Извлечение утверждений и сравнение источников…</span>
              </div>
              <div className="progress-track">
                <span className="progress-bar" style={{ width: '65%' }} />
              </div>
            </div>
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
            <section className="panel">
              <div className="panel-header">
                <h2>Описание товара</h2>
              </div>
              <div className="panel-body" style={{ whiteSpace: 'pre-wrap' }}>
                {product.description || (
                  <span className="muted">Описание не заполнено. Добавьте текст карточки — из него система извлекает утверждения.</span>
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Характеристики</h2>
              </div>
              <div className="panel-body">
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
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Состояние проверки</h2>
              </div>
              <div className="panel-body">
                {lastRun ? (
                  <>
                    <dl className="kv-list">
                      <dt>Последний запуск</dt>
                      <dd>{formatDate(lastRun.finished_at ?? lastRun.created_at)}</dd>
                      <dt>Статус</dt>
                      <dd>
                        <span className="badge badge-teal">{lastRun.status}</span>
                      </dd>
                      <dt>Версия правил</dt>
                      <dd>{lastRun.rules_version}</dd>
                      <dt>Провайдер</dt>
                      <dd>{lastRun.provider_name}</dd>
                      <dt>Утверждений</dt>
                      <dd>{String(lastSummary.claims_total ?? 0)}</dd>
                      <dt>Результатов</dt>
                      <dd>{String(lastSummary.findings_total ?? 0)}</dd>
                    </dl>
                    <button
                      type="button"
                      className="btn btn-primary"
                      style={{ marginTop: 'var(--sp-4)' }}
                      onClick={() => void runAnalysis()}
                      disabled={running}
                    >
                      <IconChecks size={16} />
                      Запустить проверку заново
                    </button>
                  </>
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
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Ограничения анализа</h2>
              </div>
              <div className="panel-body">
                {lastRun?.limitations?.length ? (
                  <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-2)', fontSize: 14 }}>
                    {lastRun.limitations.map((item) => (
                      <li key={item} style={{ marginBottom: 6 }}>
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">
                    Ограничения появятся после первого запуска проверки. Проверка всегда выполняется
                    только по предоставленным материалам.
                  </p>
                )}
              </div>
            </section>
          </div>
        )}

        {tab === 'sources' && <SourcesTab productId={product.id} />}
        {tab === 'claims' && <ClaimsTab productId={product.id} reloadKey={reloadKey} />}
        {tab === 'findings' && <FindingsTab productId={product.id} reloadKey={reloadKey} />}
        {tab === 'evidence' && <EvidenceTab productId={product.id} reloadKey={reloadKey} />}

        {tab === 'runs' && (
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Запуски проверки ({runs.length})</h2>
                <p>Каждый запуск сохраняет версию правил, провайдера и сводку результата</p>
              </div>
            </div>

            {runs.length === 0 ? (
              <div className="panel-body">
                <EmptyState
                  title="Запусков пока нет"
                  description="Запустите проверку кнопкой «Проверить карточку»."
                  icon={<IconFile size={22} />}
                />
              </div>
            ) : (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Статус</th>
                      <th>Правила</th>
                      <th>Провайдер</th>
                      <th>Утверждений</th>
                      <th>Результатов</th>
                      <th>Отчёт</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((run) => (
                      <tr key={run.id}>
                        <td className="muted">{formatDate(run.created_at)}</td>
                        <td>
                          <span className="badge badge-teal">{run.status}</span>
                        </td>
                        <td className="muted">{run.rules_version}</td>
                        <td className="muted">{run.provider_name}</td>
                        <td>{String(run.summary?.claims_total ?? 0)}</td>
                        <td>{String(run.summary?.findings_total ?? 0)}</td>
                        <td>
                          <Link
                            className="btn btn-sm"
                            to={`/app/products/${product.id}/report/${run.id}`}
                          >
                            <IconPrint size={14} />
                            Открыть
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </>
  )
}
