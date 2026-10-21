import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ProductSummary } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from '../components/States'
import { formatDate } from '../components/labels'

const MARKETPLACE_LABELS: Record<string, string> = {
  ozon: 'Ozon',
  wildberries: 'Wildberries',
  demo: 'Демо',
  other: 'Другой',
}

export function ProductsPage() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const load = useCallback(async (query: string) => {
    setError(null)
    try {
      setProducts(await api.listProducts(query))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить список товаров')
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(search), 250)
    return () => window.clearTimeout(timer)
  }, [load, search])

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Удалить товар «${name}» вместе с источниками и находками?`)) {
      return
    }
    try {
      await api.deleteProduct(id)
      await load(search)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить товар')
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Товары</h1>
          <div className="topbar-subtitle">Карточки вашего рабочего пространства</div>
        </div>
        <Link className="btn btn-primary" to="/products/new">
          + Создать товар
        </Link>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load(search)} />}

        <div className="toolbar">
          <div className="field">
            <label htmlFor="search" className="small">
              Поиск по названию, артикулу или категории
            </label>
            <input
              id="search"
              type="search"
              value={search}
              placeholder="Например, наушники"
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        {!products && !error && (
          <div className="card">
            <Skeleton rows={5} />
          </div>
        )}

        {products && products.length === 0 && (
          <EmptyState
            title="Товаров пока нет"
            description="Создайте первый товар: укажите название, описание и характеристики, добавьте документы и запустите проверку."
            action={
              <Link className="btn btn-primary" to="/products/new">
                Создать товар
              </Link>
            }
          />
        )}

        {products && products.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Маркетплейс</th>
                  <th>Источники</th>
                  <th>Находки</th>
                  <th>Последняя проверка</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <td>
                      <Link to={`/products/${product.id}`}>
                        <strong>{product.name}</strong>
                      </Link>
                      <div className="small muted">
                        {product.category || 'Категория не указана'}
                        {product.sku ? ` · ${product.sku}` : ''}
                      </div>
                    </td>
                    <td>
                      <span className="badge">
                        {MARKETPLACE_LABELS[product.marketplace] ?? product.marketplace}
                      </span>
                      {product.is_demo && (
                        <span className="badge badge-medium" style={{ marginLeft: 6 }}>
                          демо
                        </span>
                      )}
                    </td>
                    <td>{product.sources_total}</td>
                    <td>
                      {product.findings_open > 0 ? (
                        <span className="badge badge-medium">
                          {product.findings_open} открыто
                        </span>
                      ) : (
                        <span className="badge badge-success">нет открытых</span>
                      )}
                      <span className="small muted"> всего {product.findings_total}</span>
                    </td>
                    <td className="muted">
                      {product.last_run_at ? formatDate(product.last_run_at) : 'не запускалась'}
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => navigate(`/products/${product.id}/edit`)}
                        >
                          Изменить
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => void handleDelete(product.id, product.name)}
                        >
                          Удалить
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
    </>
  )
}
