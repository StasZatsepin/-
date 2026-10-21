import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { api } from '../api/client'
import type { Source } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from './States'
import { SOURCE_TYPE_LABELS, formatBytes, formatDate } from './labels'

interface SourcesTabProps {
  productId: string
}

const MANUAL_TYPES = [
  { value: 'user_note', label: 'Заметка продавца' },
  { value: 'review_export', label: 'Отзывы покупателей' },
  { value: 'technical_document', label: 'Текст документа' },
  { value: 'other', label: 'Прочее' },
]

export function SourcesTab({ productId }: SourcesTabProps) {
  const [sources, setSources] = useState<Source[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const [manualName, setManualName] = useState('')
  const [manualType, setManualType] = useState('user_note')
  const [manualText, setManualText] = useState('')
  const [manualModel, setManualModel] = useState('')
  const [manualValidUntil, setManualValidUntil] = useState('')
  const [manualSaving, setManualSaving] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      setSources(await api.listSources(productId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить источники')
    }
  }, [productId])

  useEffect(() => {
    void load()
  }, [load])

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const file = fileInput.current?.files?.[0]
    if (!file) {
      setError('Выберите файл для загрузки')
      return
    }
    setUploading(true)
    setError(null)
    setNotice(null)
    const form: Record<string, string> = {}
    const modelInput = document.getElementById('applies-to-model') as HTMLInputElement | null
    if (modelInput?.value) form.applies_to_model = modelInput.value
    const validUntilInput = document.getElementById('valid-until') as HTMLInputElement | null
    if (validUntilInput?.value) form.valid_until = validUntilInput.value

    try {
      const created = await api.uploadSource(productId, file, form)
      setNotice(
        created.extraction_status === 'extracted'
          ? `Файл «${created.source_name}» загружен, текст извлечён.`
          : `Файл «${created.source_name}» загружен. ${created.extraction_note}`,
      )
      if (fileInput.current) fileInput.current.value = ''
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить файл')
    } finally {
      setUploading(false)
    }
  }

  async function handleManualSubmit(event: FormEvent) {
    event.preventDefault()
    setManualSaving(true)
    setError(null)
    try {
      await api.createManualSource(productId, {
        source_name: manualName.trim(),
        source_type: manualType,
        text: manualText,
        applies_to_model: manualModel.trim() || null,
        valid_until: manualValidUntil || null,
      })
      setManualName('')
      setManualText('')
      setManualModel('')
      setManualValidUntil('')
      setShowManual(false)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить источник')
    } finally {
      setManualSaving(false)
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Удалить источник «${name}»?`)) return
    try {
      await api.deleteSource(id)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить источник')
    }
  }

  return (
    <div className="stack">
      {error && <ErrorMessage message={error} />}
      {notice && <div className="alert alert-success">{notice}</div>}

      <div className="card">
        <div className="card-header">
          <div>
            <h2>Загрузить источник</h2>
            <p>Поддерживаются TXT, CSV, MD, XLSX и PDF с текстовым слоем.</p>
          </div>
        </div>
        <form onSubmit={handleUpload}>
          <div className="form-row">
            <div className="field">
              <label htmlFor="source-file">Файл</label>
              <input id="source-file" ref={fileInput} type="file" accept=".txt,.csv,.md,.pdf,.xlsx" />
            </div>
            <div className="field">
              <label htmlFor="applies-to-model">Область применения (модель)</label>
              <input
                id="applies-to-model"
                type="text"
                placeholder="необязательно, например DEMO-X500"
              />
            </div>
            <div className="field">
              <label htmlFor="valid-until">Действует до</label>
              <input id="valid-until" type="date" />
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={uploading}>
              {uploading ? 'Загружаем…' : 'Загрузить файл'}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => setShowManual((current) => !current)}
            >
              {showManual ? 'Скрыть ввод вручную' : 'Ввести вручную'}
            </button>
          </div>
        </form>

        {showManual && (
          <form onSubmit={handleManualSubmit} style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
            <div className="form-row">
              <div className="field">
                <label htmlFor="manual-name">Название источника *</label>
                <input
                  id="manual-name"
                  type="text"
                  value={manualName}
                  required
                  onChange={(event) => setManualName(event.target.value)}
                  placeholder="Отзывы покупателей за май"
                />
              </div>
              <div className="field">
                <label htmlFor="manual-type">Тип</label>
                <select
                  id="manual-type"
                  value={manualType}
                  onChange={(event) => setManualType(event.target.value)}
                >
                  {MANUAL_TYPES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="manual-model">Модель в области применения</label>
                <input
                  id="manual-model"
                  type="text"
                  value={manualModel}
                  onChange={(event) => setManualModel(event.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="manual-valid">Действует до</label>
                <input
                  id="manual-valid"
                  type="date"
                  value={manualValidUntil}
                  onChange={(event) => setManualValidUntil(event.target.value)}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="manual-text">Текст *</label>
              <textarea
                id="manual-text"
                value={manualText}
                required
                rows={6}
                onChange={(event) => setManualText(event.target.value)}
                placeholder="Текст отзывов: каждый отзыв с новой строки или разделён пустой строкой."
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={manualSaving}>
                {manualSaving ? 'Сохраняем…' : 'Сохранить источник'}
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h2>Источники товара ({sources?.length ?? 0})</h2>
            <p>
              Каждый источник хранит дату, хеш содержимого и результат извлечения текста.
            </p>
          </div>
        </div>

        {!sources && <Skeleton rows={4} />}

        {sources && sources.length === 0 && (
          <EmptyState
            title="Источников пока нет"
            description="Загрузите документ, файл отзывов или введите данные вручную. Без источников часть утверждений останется без подтверждения."
          />
        )}

        {sources && sources.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Тип</th>
                  <th>Дата</th>
                  <th>Размер</th>
                  <th>Разбор</th>
                  <th>Хеш</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {sources.map((source) => (
                  <tr key={source.id}>
                    <td>
                      <strong>{source.source_name}</strong>
                      {source.extraction_note && (
                        <div className="small muted">{source.extraction_note}</div>
                      )}
                      {source.text_preview && (
                        <details>
                          <summary className="small muted">Показать текст</summary>
                          <div className="excerpt">{source.text_preview}</div>
                        </details>
                      )}
                    </td>
                    <td>
                      <span className="badge">
                        {SOURCE_TYPE_LABELS[source.source_type] ?? source.source_type}
                      </span>
                    </td>
                    <td className="muted">{formatDate(source.source_date ?? source.uploaded_at)}</td>
                    <td className="muted">{formatBytes(source.size_bytes)}</td>
                    <td>
                      <span
                        className={`badge ${
                          source.extraction_status === 'extracted'
                            ? 'badge-success'
                            : source.extraction_status === 'needs_ocr'
                              ? 'badge-medium'
                              : 'badge-info'
                        }`}
                      >
                        {source.extraction_status}
                      </span>
                    </td>
                    <td className="mono muted">{source.content_hash.slice(0, 12)}…</td>
                    <td>
                      <div className="table-actions">
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => void handleDelete(source.id, source.source_name)}
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
    </div>
  )
}
