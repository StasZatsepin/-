import { useCallback, useEffect, useRef, useState } from 'react'
import type { DragEvent, FormEvent } from 'react'
import { api } from '../api/client'
import type { Source } from '../api/types'
import { EmptyState, ErrorMessage, Skeleton } from './States'
import { SOURCE_TYPE_LABELS, formatBytes, formatDate , formatCount } from './labels'
import { IconFile, IconInfo, IconTrash, IconUpload } from './icons'

interface SourcesTabProps {
  productId: string
}

const MANUAL_TYPES = [
  { value: 'user_note', label: 'Заметка продавца' },
  { value: 'review_export', label: 'Отзывы покупателей' },
  { value: 'technical_document', label: 'Текст документа' },
  { value: 'other', label: 'Прочее' },
]

const EXTRACTION_BADGE: Record<string, string> = {
  extracted: 'badge-teal',
  needs_ocr: 'badge-warn',
  empty: 'badge-neutral',
  failed: 'badge-danger',
  pending: 'badge-neutral',
}

const EXTRACTION_LABELS: Record<string, string> = {
  extracted: 'текст извлечён',
  needs_ocr: 'нужен OCR',
  empty: 'нет текста',
  failed: 'ошибка разбора',
  pending: 'ожидает',
}

export function SourcesTab({ productId }: SourcesTabProps) {
  const [sources, setSources] = useState<Source[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const [dragOver, setDragOver] = useState(false)
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

  async function uploadFile(file: File) {
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

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragOver(false)
    const file = event.dataTransfer.files?.[0]
    if (file) void uploadFile(file)
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
      {notice && (
        <div className="alert alert-success">
          <span className="alert-icon">
            <IconInfo size={16} />
          </span>
          <div>{notice}</div>
        </div>
      )}

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Добавить источник</h2>
            <p>Поддерживаются TXT, CSV, MD, XLSX и PDF с текстовым слоем</p>
          </div>
        </div>
        <div className="panel-body">
          <div className="alert alert-warn" style={{ marginBottom: 'var(--sp-4)' }}>
            <span className="alert-icon">
              <IconInfo size={16} />
            </span>
            <div>
              <strong>Внимание:</strong> в публичной демоверсии загруженные файлы хранятся во
              временном хранилище и <strong>будут удалены при перезапуске или обновлении
              приложения</strong>. Для постоянного хранения подключите S3-совместимое
              хранилище (Cloudflare R2, AWS S3 и т.п.).
            </div>
          </div>

          <div
            className={dragOver ? 'dropzone is-over' : 'dropzone'}
            role="button"
            tabIndex={0}
            onClick={() => fileInput.current?.click()}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                fileInput.current?.click()
              }
            }}
            onDragOver={(event) => {
              event.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <span className="dropzone-icon">
              <IconUpload size={20} />
            </span>
            <strong>{uploading ? 'Загружаем и разбираем файл…' : 'Перетащите файл сюда'}</strong>
            <span>или нажмите, чтобы выбрать. Максимальный размер — 10 МБ</span>
            <input
              ref={fileInput}
              type="file"
              accept=".txt,.csv,.md,.pdf,.xlsx"
              style={{ display: 'none' }}
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void uploadFile(file)
              }}
            />
          </div>

          <div className="form-row" style={{ marginTop: 'var(--sp-4)' }}>
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

          <button
            type="button"
            className="btn"
            onClick={() => setShowManual((current) => !current)}
          >
            {showManual ? 'Скрыть ввод вручную' : 'Ввести данные вручную'}
          </button>

          {showManual && (
            <form
              onSubmit={handleManualSubmit}
              style={{
                marginTop: 'var(--sp-5)',
                paddingTop: 'var(--sp-5)',
                borderTop: '1px solid var(--border)',
              }}
            >
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
                <div className="field-hint">
                  В отзывах полезно указывать оценку и дату — система использует их как контекст сигнала.
                </div>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={manualSaving}>
                  {manualSaving ? 'Сохраняем…' : 'Сохранить источник'}
                </button>
              </div>
            </form>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Источники товара ({formatCount(sources?.length ?? 0, ['источник', 'источника', 'источников'])})</h2>
            <p>Для каждого источника хранятся дата, хеш содержимого и результат извлечения текста</p>
          </div>
        </div>

        {!sources && (
          <div className="panel-body">
            <Skeleton rows={4} />
          </div>
        )}

        {sources && sources.length === 0 && (
          <div className="panel-body">
            <EmptyState
              title="Источников пока нет"
              description="Загрузите документ, файл отзывов или введите данные вручную. Без источников часть утверждений останется без подтверждения."
              icon={<IconFile size={22} />}
            />
          </div>
        )}

        {sources && sources.length > 0 && (
          <div className="table-wrap">
            <table className="data">
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
                      <span className="cell-title">{source.source_name}</span>
                      {source.extraction_note && (
                        <div className="cell-sub">{source.extraction_note}</div>
                      )}
                      {source.text_preview && (
                        <details>
                          <summary className="small muted" style={{ cursor: 'pointer' }}>
                            Показать текст
                          </summary>
                          <div className="excerpt">{source.text_preview}</div>
                        </details>
                      )}
                    </td>
                    <td>
                      <span className="badge badge-neutral">
                        {SOURCE_TYPE_LABELS[source.source_type] ?? source.source_type}
                      </span>
                    </td>
                    <td className="muted">{formatDate(source.source_date ?? source.uploaded_at)}</td>
                    <td className="muted">{formatBytes(source.size_bytes)}</td>
                    <td>
                      <span className={`badge ${EXTRACTION_BADGE[source.extraction_status] ?? 'badge-neutral'}`}>
                        {EXTRACTION_LABELS[source.extraction_status] ?? source.extraction_status}
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
        )}
      </section>
    </div>
  )
}
