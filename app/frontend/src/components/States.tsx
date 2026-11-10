import type { ReactNode } from 'react'
import { IconInfo } from './icons'

export function Loading({ label = 'Загрузка…' }: { label?: string }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton" style={{ width: `${92 - index * 11}%` }} />
      ))}
    </div>
  )
}

export function ErrorMessage({
  message,
  onRetry,
  title = 'Не удалось выполнить действие',
}: {
  message: string
  onRetry?: () => void
  title?: string
}) {
  return (
    <div className="alert alert-error" role="alert">
      <span className="alert-icon" aria-hidden="true">
        <IconInfo size={16} />
      </span>
      <div>
        <strong>{title}</strong>
        {message}
        {onRetry && (
          <div style={{ marginTop: 10 }}>
            <button type="button" className="btn btn-sm" onClick={onRetry}>
              Повторить
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="empty-state">
      {icon ? (
        <span className="empty-state-icon" aria-hidden="true">
          {icon}
        </span>
      ) : (
        <EmptyIllustration />
      )}
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}

/** Иллюстрация пустого экрана: карточка товара и лупа над одной из строк. */
function EmptyIllustration() {
  return (
    <svg className="empty-illustration" width="132" height="96" viewBox="0 0 132 96" fill="none" aria-hidden="true">
      <rect x="14" y="10" width="84" height="76" rx="10" fill="var(--surface-3)" stroke="var(--border)" strokeWidth="2" />
      <rect x="26" y="24" width="40" height="7" rx="3.5" fill="var(--border)" />
      <rect x="26" y="40" width="60" height="6" rx="3" fill="var(--border)" />
      <rect x="26" y="54" width="48" height="6" rx="3" fill="var(--border)" />
      <rect x="26" y="68" width="30" height="6" rx="3" fill="var(--border)" />
      <g className="empty-lens">
        <circle cx="94" cy="56" r="16" fill="var(--surface)" stroke="var(--text-3)" strokeWidth="3" />
        <path d="M106 68l12 12" stroke="var(--text-3)" strokeWidth="4" strokeLinecap="round" />
        <path d="M87 56h14" stroke="var(--text-3)" strokeWidth="3" strokeLinecap="round" />
      </g>
    </svg>
  )
}
