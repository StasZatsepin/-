import { useState } from 'react'
import { api, ApiError } from '../api/client'
import type { QuickCheckResult } from '../api/types'
import { FINDING_TYPE_LABELS, SEVERITY_BADGE, SEVERITY_LABELS } from './labels'
import { SuggestionBlock } from './SuggestionBlock'

const SAMPLE = {
  description:
    'Умные часы с AMOLED-экраном. Время работы без подзарядки — до 48 часов. Идеально подходят для спорта и поездок.',
  attributes: 'Время работы: 30 ч\nМатериал корпуса: алюминий',
}

/** Подсвечивает в тексте фрагмент, найденный правилом (если он есть в тексте дословно). */
function Highlighted({ text, marks }: { text: string; marks: string[] }) {
  const needles = marks.map((m) => m.trim()).filter((m) => m.length > 2 && text.includes(m))
  if (needles.length === 0) return <>{text}</>
  const escaped = needles.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const parts = text.split(new RegExp(`(${escaped.join('|')})`, 'g'))
  return (
    <>
      {parts.map((part, i) => (needles.includes(part) ? <mark key={i}>{part}</mark> : <span key={i}>{part}</span>))}
    </>
  )
}

export function QuickCheck() {
  const [description, setDescription] = useState('')
  const [attributes, setAttributes] = useState('')
  const [reviews, setReviews] = useState('')
  const [document, setDocument] = useState('')
  const [extra, setExtra] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<QuickCheckResult | null>(null)
  const [checkedText, setCheckedText] = useState('')

  async function run(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    if (description.trim().length < 10) {
      setError('Вставьте описание товара: хотя бы одно-два предложения.')
      return
    }
    setBusy(true)
    try {
      const data = await api.quickCheck({
        description,
        attributes_text: attributes,
        document_text: document,
        reviews_text: reviews,
      })
      setResult(data)
      setCheckedText(description)
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError('Слишком много проверок подряд. Подождите минуту и повторите.')
      } else if (err instanceof ApiError && err.status === 422) {
        setError('Проверьте поля: описание не короче 10 символов, тексты не слишком длинные.')
      } else {
        setError('Сервер сейчас не отвечает. Он может просыпаться после простоя — повторите через полминуты.')
      }
    } finally {
      setBusy(false)
    }
  }

  function fillSample() {
    setDescription(SAMPLE.description)
    setAttributes(SAMPLE.attributes)
    setResult(null)
    setError('')
  }

  const marks = result
    ? result.findings.flatMap((f) =>
        f.source_refs
          .filter((r) => r.relation !== 'supports')
          .map((r) => r.excerpt.replace(/\s+/g, ' ').trim()),
      )
    : []

  return (
    <form className="quick-form" onSubmit={run} noValidate>
      <div className="field">
        <label htmlFor="qc-desc">Описание товара</label>
        <textarea
          id="qc-desc"
          rows={5}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Вставьте текст из карточки: описание, обещания, преимущества"
        />
      </div>
      <div className="field">
        <label htmlFor="qc-attrs">Характеристики</label>
        <textarea
          id="qc-attrs"
          rows={4}
          value={attributes}
          onChange={(e) => setAttributes(e.target.value)}
          placeholder={'По одной на строку: «Название: значение»\nВремя работы: 30 ч'}
        />
        <span className="field-hint">Без характеристик система найдёт только размытые обещания и утверждения без подтверждения.</span>
      </div>

      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExtra(!extra)} aria-expanded={extra}>
        {extra ? 'Скрыть' : 'Добавить'} документ и отзывы
      </button>
      {extra && (
        <>
          <div className="field">
            <label htmlFor="qc-doc">Текст документа (паспорт, сертификат)</label>
            <textarea id="qc-doc" rows={3} value={document} onChange={(e) => setDocument(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="qc-rev">Отзывы — по одному на строку</label>
            <textarea id="qc-rev" rows={3} value={reviews} onChange={(e) => setReviews(e.target.value)} />
          </div>
        </>
      )}

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <div className="quick-actions">
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Проверяем…' : 'Проверить'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={fillSample} disabled={busy}>
          Подставить пример
        </button>
      </div>
      <p className="field-hint">Ничего не сохраняется: текст обрабатывается в памяти и сразу забывается.</p>

      {result && (
        <div className="quick-result" aria-live="polite">
          <h3>
            {result.total === 0 ? 'Расхождений не найдено' : `Найдено замечаний: ${result.total}`}
          </h3>
          {result.note && <p className="field-hint">{result.note}</p>}
          {result.total > 0 && (
            <blockquote className="quick-source">
              <Highlighted text={checkedText} marks={marks} />
            </blockquote>
          )}
          <ul className="quick-list">
            {result.findings.map((f, i) => (
              <li key={i} className="quick-item">
                <div className="finding-meta">
                  <span className={`badge ${SEVERITY_BADGE[f.severity]}`}>{SEVERITY_LABELS[f.severity]}</span>
                  <span className="badge badge-neutral">{FINDING_TYPE_LABELS[f.finding_type]}</span>
                </div>
                <p className="finding-text">{f.description}</p>
                {f.suggestion?.text && <SuggestionBlock text={f.suggestion.text} copyText={f.suggestion.copy_text} />}
              </li>
            ))}
          </ul>
        </div>
      )}
    </form>
  )
}
