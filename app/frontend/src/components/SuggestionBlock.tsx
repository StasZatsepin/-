import { useState } from 'react'
import { IconCheck } from './icons'

/** Готовая формулировка «что исправить» с кнопкой копирования. */
export function SuggestionBlock({ text, copyText }: { text: string; copyText?: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    const value = copyText || text
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="callout callout-fix">
      <span className="callout-icon" aria-hidden="true">
        <IconCheck size={16} />
      </span>
      <div>
        <strong>Что исправить</strong>
        {text}
        <div>
          <button type="button" className="btn btn-ghost btn-sm suggestion-copy" onClick={copy}>
            {copied ? 'Скопировано' : copyText ? 'Скопировать значение' : 'Скопировать текст'}
          </button>
        </div>
      </div>
    </div>
  )
}
