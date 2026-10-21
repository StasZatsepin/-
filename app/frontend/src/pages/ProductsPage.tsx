import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ProductSummary } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from '../components/States'
import { MARKETPLACE_LABELS, formatCount, formatDate } from '../components/labels'
import { IconEdit, IconPlus, IconSearch, IconTrash } from '../components/icons'

type SortKey = 'name' | 'updated' | 'findings'

export function ProductsPage() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sort, setSort] = useState<SortKey>('updated')
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

  const sorted = useMemo(() => {
    const list = [...(products ?? [])]
    if (sort === 'name') {
      list.sort((first, second) => first.name.localeCompare(second.name, 'ru'))
    } else if (sort === 'findings') {
      list.sort((first, second) => second.findings_open - first.findings_open)
    } else {
      list.sort(
        (first, second) =>
          new Date(second.updated_at).getTime() - new Date(first.updated_at).getTime(),
      )
    }
    return list
  }, [products, sort])

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Удалить товар «${name}» вместе с источниками и результатами?`)) {
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
        <div className="topbar-titles">
          <h1>Товары</h1>
          <div className="topbar-subtitle">
            {products
              ? formatCount(products.length, ['карточка', 'карточки', 'карточек'])
              : 'Загрузка…'}
          </div>
        </div>
        <div className="topbar-actions">
          <Link className="btn btn-primary" to="/app/products/new">
            <IconPlus size={16} />
            Создать товар
          </Link>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} onRetry={() => void load(search)} />}

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Каталог карточек</h2>
              <p>Поиск по названию, артикулу и категории</p>
            </div>
            <div className="toolbar" style={{ margin: 0 }}>
              <div className="search-field">
                <span className="search-icon">
                  <IconSearch size={16} />
                </span>
                <input
                  id="catalog-search"
                  type="search"
                  value={search}
                  placeholder="Например, наушники"
                  aria-label="Поиск по товарам"
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>
            </div>
          </div>

          {!products && !error && (
            <div className="panel-body">
              <Skeleton rows={5} />
            </div>
          )}

          {products && products.length === 0 && (
            <div className="panel-body">
              <EmptyState
                title={search ? 'Ничего не найдено' : 'Товаров пока нет'}
                description={
                  search
                    ? `По запросу «${search}» карточек нет. Попробуйте другое название или сбросьте поиск.`
                    : 'Создайте первый товар: укажите название, описание и характеристики, добавьте документы и запустите проверку.'
                }
                action={
                  search ? (
                    <button type="button" className="btn" onClick={() => setSearch('')}>
                      Сбросить поиск
                    </button>
                  ) : (
                    <Link className="btn btn-primary" to="/app/products/new">
                      Создать товар
                    </Link>
                  )
                }
              />
            </div>
          )}

          {products && products.length > 0 && (
            <>
              <div className="toolbar" style={{ padding: '0 var(--sp-6)', marginTop: 'var(--sp-4)' }}>
                <div className="field">
                  <label htmlFor="sort" className="small">
                    Сортировка
                  </label>
                  <select
                    id="sort"
                    value={sort}
                    onChange={(event) => setSort(event.target.value as SortKey)}
                    style={{ minWidth: 220 }}
                  >
                    <option value="updated">По изменению</option>
                    <option value="name">По названию</option>
                    <option value="findings">По числу открытых результатов</option>
                  </select>
                </div>
              </div>

              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Название</th>
                      <th>Маркетплейс</th>
                      <th>Источники</th>
                      <th>Результаты</th>
                      <th>Последняя проверка</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((product) => (
                      <tr
                        key={product.id}
                        className="is-clickable"
                        onClick={() => navigate(`/app/products/${product.id}`)}
                      >
                        <td>
                          <Link
                            to={`/app/products/${product.id}`}
                            className="cell-title"
                            style={{ color: 'var(--text)' }}
                            onClick={(event) => event.stopPropagation()}
                          >
                            {product.name}
                          </Link>
                          <div className="cell-sub">
                            {product.category || 'Категория не указана'}
                            {product.sku ? ` · ${product.sku}` : ''}
                          </div>
                        </td>
                        <td>
                          <span className="badge badge-neutral">
                            {MARKETPLACE_LABELS[product.marketplace] ?? product.marketplace}
                          </span>
                          {product.is_demo && (
                            <span className="badge badge-violet" style={{ marginLeft: 6 }}>
                              демо
                            </span>
                          )}
                        </td>
                        <td className="muted">{product.sources_total}</td>
                        <td>
                          {product.findings_open > 0 ? (
                            <span className="badge badge-warn">{product.findings_open} к разбору</span>
                          ) : (
                            <span className="badge badge-teal">открытых нет</span>
                          )}
                          <div className="cell-sub">всего {product.findings_total}</div>
                        </td>
                        <td className="muted">
                          {product.last_run_at ? formatDate(product.last_run_at) : 'не запускалась'}
                        </td>
                        <td>
                          <div className="table-actions">
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={(event) => {
                                event.stopPropagation()
                                navigate(`/app/products/${product.id}/edit`)
                              }}
                            >
                              <IconEdit size={14} />
                              Изменить
                            </button>
                            <button
                              type="button"
                              className="btn btn-sm btn-danger"
                              onClick={(event) => {
                                event.stopPropagation()
                                void handleDelete(product.id, product.name)
                              }}
                            >
                              <IconTrash size={14} />
                              Удалить
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
