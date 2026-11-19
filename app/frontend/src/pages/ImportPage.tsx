import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { ImportPreview } from '../api/types'
import { ErrorMessage } from '../components/States'
import { IconUpload } from '../components/icons'

const FIELD_LABELS: Record<string, string> = {
  name: 'Название товара (обязательно)',
  sku: 'Артикул (SKU)',
  marketplace: 'Маркетплейс',
  category: 'Категория',
  description: 'Описание',
  attributes: 'Характеристики («Ключ: значение», по строке)',
}

export function ImportPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [mapping, setMapping] = useState<Record<string, number | null>>({})
  const [skipInvalid, setSkipInvalid] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  async function loadPreview(next: File, nextMapping?: Record<string, number | null>) {
    setBusy(true)
    setError(null)
    try {
      const data = await api.importPreview(next, nextMapping)
      setPreview(data)
      setMapping(data.mapping)
    } catch (err) {
      setPreview(null)
      setError(err instanceof Error ? err.message : 'Не удалось прочитать файл')
    } finally {
      setBusy(false)
    }
  }

  function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null
    setFile(chosen)
    setPreview(null)
    if (chosen) void loadPreview(chosen)
  }

  function onMap(field: string, value: string) {
    const next = { ...mapping, [field]: value === '' ? null : Number(value) }
    setMapping(next)
    if (file) void loadPreview(file, next)
  }

  async function commit() {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      await api.importCommit(file, mapping, skipInvalid)
      navigate('/app/products')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать')
      setBusy(false)
    }
  }

  const summary = preview?.summary
  const hasInvalid = !!summary && summary.ok < summary.total

  return (
    <>
      <header className="topbar">
        <div className="topbar-titles">
          <h1>Импорт каталога</h1>
          <div className="topbar-subtitle">Файл CSV или XLSX, до 2000 строк и 5 МБ</div>
        </div>
        <div className="topbar-actions">
          <Link className="btn" to="/app/products">
            К списку товаров
          </Link>
        </div>
      </header>
      <div className="content">
        {error && <ErrorMessage message={error} />}

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>1. Выберите файл</h2>
              <p>Первая строка должна содержать названия столбцов. Файл не сохраняется на сервере.</p>
            </div>
          </div>
          <div className="panel-body">
            <label className="btn" htmlFor="import-file">
              <IconUpload size={16} />
              {file ? file.name : 'Выбрать файл'}
            </label>
            <input id="import-file" type="file" accept=".csv,.xlsx,.txt" onChange={onFile} style={{ display: 'none' }} />
          </div>
        </div>

        {preview && (
          <>
            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>2. Сопоставьте столбцы</h2>
                  <p>Система предложила вариант по названиям столбцов. Проверьте и при необходимости измените.</p>
                </div>
              </div>
              <div className="panel-body import-mapping">
                {Object.entries(FIELD_LABELS).map(([field, label]) => (
                  <div className="field" key={field}>
                    <label htmlFor={`map-${field}`}>{label}</label>
                    <select
                      id={`map-${field}`}
                      value={mapping[field] ?? ''}
                      onChange={(event) => onMap(field, event.target.value)}
                    >
                      <option value="">— не использовать —</option>
                      {preview.headers.map((header, index) => (
                        <option key={index} value={index}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
              <div className="table-wrap">
                <table className="data stack">
                  <thead>
                    <tr>
                      {preview.headers.map((header, index) => (
                        <th key={index}>{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample.map((row, index) => (
                      <tr key={index}>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} data-label={preview.headers[cellIndex]}>
                            {cell.length > 80 ? `${cell.slice(0, 80)}…` : cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <h2>3. Проверка строк</h2>
                  <p>
                    {summary
                      ? `Всего ${summary.total}: к импорту ${summary.ok}, ошибок ${summary.error}, повторов ${summary.duplicate}.`
                      : 'Укажите столбец с названием товара.'}
                  </p>
                </div>
              </div>
              <div className="panel-body">
                {preview.problems.length > 0 && (
                  <ul className="import-problems">
                    {preview.problems.map((problem) => (
                      <li key={problem.line}>
                        <strong>Строка {problem.line}</strong>
                        {problem.name ? ` («${problem.name}»)` : ''}: {problem.messages.join(' ')}
                      </li>
                    ))}
                  </ul>
                )}
                {hasInvalid && (
                  <label className="import-skip">
                    <input type="checkbox" checked={skipInvalid} onChange={(e) => setSkipInvalid(e.target.checked)} />
                    Пропустить некорректные и повторяющиеся строки, импортировать остальные
                  </label>
                )}
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy || !summary || summary.ok === 0 || (hasInvalid && !skipInvalid)}
                  onClick={() => void commit()}
                >
                  {busy ? 'Подождите…' : `Импортировать${summary ? ` (${summary.ok})` : ''}`}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
