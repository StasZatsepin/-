/**
 * Знак продукта и текстовый логотип.
 *
 * Идея знака: квадрат, разделённый по диагонали. Заполненная часть — «проверенное
 * основание», светлая — «обещание». Форма читается даже в 24px.
 */

interface LogoProps {
  size?: number
  variant?: 'light' | 'dark'
}

export function LogoMark({ size = 34, variant = 'light' }: LogoProps) {
  const background = variant === 'light' ? 'var(--accent)' : 'rgba(255,255,255,0.1)'
  const foreground = variant === 'light' ? '#ffffff' : 'var(--text-inverse)'

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      style={{ flexShrink: 0 }}
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="9" fill={background} />
      <path d="M7 25 25 7" stroke={foreground} strokeOpacity="0.32" strokeWidth="1.6" />
      <path d="M7 25V13a6 6 0 0 1 6-6h6Z" fill={foreground} fillOpacity="0.92" />
      <circle cx="12.5" cy="18.5" r="2.1" fill={background} />
    </svg>
  )
}

interface WordmarkProps {
  variant?: 'light' | 'dark'
  compact?: boolean
}

export function LogoWordmark({ variant = 'light', compact = false }: WordmarkProps) {
  return (
    <span className={`brand-text brand-text--${variant}`}>
      <strong>
        Обещание
        <br />
        против реальности
      </strong>
      {!compact && <span className="brand-sub">Проверка заявлений</span>}
    </span>
  )
}
