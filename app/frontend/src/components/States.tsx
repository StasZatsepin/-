import type { ReactNode } from 'react'
import { IconInfo, IconSearch } from './icons'

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
      <span className="empty-state-icon" aria-hidden="true">
        {icon ?? <IconSearch size={22} />}
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}
