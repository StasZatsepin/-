import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { Product } from '../api/types'
import { ErrorMessage, Loading } from '../components/States'
import { IconInfo, IconPlus, IconTrash } from '../components/icons'

interface AttributeRow {
  key: string
  value: string
}

const MARKETPLACES = [
  { value: 'ozon', label: 'Ozon' },
  { value: 'wildberries', label: 'Wildberries' },
  { value: 'other', label: 'Другой маркетплейс' },
  { value: 'demo', label: 'Демонстрационный' },
]

export function ProductFormPage() {
  const { productId } = useParams()
  const isEdit = Boolean(productId)
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [marketplace, setMarketplace] = useState('other')
  const [sku, setSku] = useState('')
  const [description, setDescription] = useState('')
  const [attributes, setAttributes] = useState<AttributeRow[]>([])
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const load = useCallback(async () => {
    if (!productId) return
    setLoading(true)
    try {
      const product: Product = await api.getProduct(productId)
      setName(product.name)
      setCategory(product.category)
      setMarketplace(product.marketplace)
      setSku(product.sku)
      setDescription(product.description)
      setAttributes(
        Object.entries(product.attributes ?? {}).map(([key, value]) => ({
          key,
          value: String(value),
        })),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить товар')
    } finally {
      setLoading(false)
    }
  }, [productId])

  useEffect(() => {
    void load()
  }, [load])

  function updateAttribute(index: number, patch: Partial<AttributeRow>) {
    setAttributes((current) =>
      current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)),
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setFieldErrors({})

    const attributesObject: Record<string, unknown> = {}
    for (const row of attributes) {
      const key = row.key.trim()
      if (!key) continue
      const raw = row.value.trim()
      if (raw === '') continue
      const numeric = Number(raw.replace(',', '.'))
      attributesObject[key] = Number.isFinite(numeric) && raw !== '' ? numeric : raw
    }

    const payload = {
      name: name.trim(),
      category: category.trim(),
      marketplace,
      sku: sku.trim(),
      description,
      attributes: attributesObject,
    }

    try {
      const saved = productId
        ? await api.updateProduct(productId, payload)
        : await api.createProduct(payload)
      navigate(`/app/products/${saved.id}`)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.userMessage)
        const details: Record<string, string> = {}
        err.details.forEach((detail) => {
          if (detail.field) details[detail.field] = detail.message
        })
        setFieldErrors(details)
      } else {
        setError('Не удалось сохранить товар')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="content">
        <Loading label="Загружаем товар…" />
      </div>
    )
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-titles">
          <h1>{isEdit ? 'Редактирование товара' : 'Новый товар'}</h1>
          <div className="topbar-subtitle">
            {isEdit
              ? 'Изменения сразу отражаются в источниках и следующих проверках'
              : 'Описание и характеристики станут первыми источниками проверки'}
          </div>
        </div>
        <div className="topbar-actions">
          <Link className="btn" to="/app/products">
            К списку
          </Link>
        </div>
      </header>

      <div className="content">
        {error && <ErrorMessage message={error} />}

        <form className="panel" onSubmit={handleSubmit}>
          <div className="panel-header">
            <div>
              <h2>Основные данные</h2>
              <p>Название обязательно. Остальные поля можно дополнить позже.</p>
            </div>
          </div>

          <div className="panel-body">
            <div className="field">
              <label htmlFor="name">Название товара *</label>
              <input
                id="name"
                type="text"
                value={name}
                required
                maxLength={255}
                onChange={(event) => setName(event.target.value)}
                placeholder="Например, беспроводные наушники X-500"
              />
              {fieldErrors.name && <div className="field-error">{fieldErrors.name}</div>}
            </div>

            <div className="form-row">
              <div className="field">
                <label htmlFor="category">Категория</label>
                <input
                  id="category"
                  type="text"
                  value={category}
                  maxLength={255}
                  onChange={(event) => setCategory(event.target.value)}
                  placeholder="электроника / наушники"
                />
              </div>
              <div className="field">
                <label htmlFor="marketplace">Маркетплейс</label>
                <select
                  id="marketplace"
                  value={marketplace}
                  onChange={(event) => setMarketplace(event.target.value)}
                >
                  {MARKETPLACES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="sku">Артикул / SKU</label>
                <input
                  id="sku"
                  type="text"
                  value={sku}
                  maxLength={120}
                  onChange={(event) => setSku(event.target.value)}
                  placeholder="необязательно"
                />
              </div>
            </div>

            <div className="field">
              <label htmlFor="description">Описание товара</label>
              <textarea
                id="description"
                value={description}
                maxLength={20000}
                rows={9}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Вставьте текст карточки: характеристики, обещания и условия. Именно из него система извлекает утверждения."
              />
              <div className="field-hint">
                Текст описания сохраняется как источник «Описание товара» и цитируется в результатах
                проверки.
              </div>
            </div>

            <div className="field">
              <label>Характеристики</label>
              <div className="field-hint" style={{ marginTop: 0, marginBottom: 12 }}>
                Ключ и значение. Числовые значения автоматически приводятся к единицам измерения
                (например, <span className="mono">battery_life_hours</span> = 30).
              </div>
              {attributes.map((row, index) => (
                <div className="attribute-row" key={index}>
                  <input
                    type="text"
                    value={row.key}
                    placeholder="battery_life_hours"
                    aria-label={`Ключ характеристики ${index + 1}`}
                    onChange={(event) => updateAttribute(index, { key: event.target.value })}
                  />
                  <input
                    type="text"
                    value={row.value}
                    placeholder="30"
                    aria-label={`Значение характеристики ${index + 1}`}
                    onChange={(event) => updateAttribute(index, { value: event.target.value })}
                  />
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    aria-label={`Удалить характеристику ${index + 1}`}
                    onClick={() =>
                      setAttributes((current) => current.filter((_, rowIndex) => rowIndex !== index))
                    }
                  >
                    <IconTrash size={14} />
                  </button>
                </div>
              ))}
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => setAttributes((current) => [...current, { key: '', value: '' }])}
              >
                <IconPlus size={14} />
                Добавить характеристику
              </button>
            </div>

            <div className="alert alert-info" style={{ marginBottom: 0 }}>
              <span className="alert-icon">
                <IconInfo size={16} />
              </span>
              <div>
                После сохранения откройте вкладку «Источники», загрузите документы и файл отзывов, а
                затем запустите проверку — система сопоставит утверждения с документами и
                характеристиками.
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Сохраняем…' : isEdit ? 'Сохранить изменения' : 'Создать товар'}
              </button>
              <Link className="btn" to="/app/products">
                Отмена
              </Link>
            </div>
          </div>
        </form>
      </div>
    </>
  )
}
