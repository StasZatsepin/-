import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { LogoMark } from '../components/Logo'
import { IconArrowRight, IconChecks, IconInfo, IconShield } from '../components/icons'
import { useAuth } from '../context/AuthContext'

type Mode = 'login' | 'register'

const HIGHLIGHTS = [
  {
    icon: IconChecks,
    title: 'Проверка без внешних сервисов',
    text: 'Детерминированные правила работают на ваших материалах. Платный API не нужен.',
  },
  {
    icon: IconShield,
    title: 'Данные остаются у вас',
    text: 'Рабочее пространство, источники и находки доступны только вам.',
  },
]

export function LoginPage() {
  const { user, login, register, enterDemo, error } = useAuth()
  const [params] = useSearchParams()
  const [mode, setMode] = useState<Mode>(params.get('demo') ? 'login' : 'login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [workspaceName, setWorkspaceName] = useState('')
  const [busy, setBusy] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (params.get('demo')) {
      void handleDemo()
    }
    // Обрабатываем параметр один раз при монтировании.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (user) {
    return <Navigate to="/app" replace />
  }

  async function handleDemo() {
    setBusy(true)
    setLocalError(null)
    try {
      await enterDemo()
      navigate('/app')
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Демо-режим недоступен')
    } finally {
      setBusy(false)
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setLocalError(null)
    try {
      if (mode === 'login') {
        await login(email.trim(), password)
      } else {
        await register(email.trim(), password, displayName.trim(), workspaceName.trim())
      }
      navigate('/app')
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Не удалось выполнить вход')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-split">
        <aside className="auth-aside">
          <div className="auth-aside-inner">
            <div className="auth-brand">
              <LogoMark size={40} variant="dark" />
              <span>
                Обещание
                <br />
                против реальности
              </span>
            </div>

            <h2>Проверяйте заявления, а не обещания</h2>
            <p>
              Сопоставляйте описания, характеристики, документы и отзывы. Каждый вывод системы
              показывает источник, ограничение и следующий шаг.
            </p>

            <ul className="auth-highlights">
              {HIGHLIGHTS.map((item) => {
                const Icon = item.icon
                return (
                  <li key={item.title}>
                    <span className="auth-highlight-icon">
                      <Icon size={17} />
                    </span>
                    <span>
                      <strong>{item.title}</strong>
                      <span>{item.text}</span>
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>
        </aside>

        <main className="auth-main">
          <div className="auth-card">
            <div className="auth-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'login'}
                className={mode === 'login' ? 'auth-tab active' : 'auth-tab'}
                onClick={() => setMode('login')}
              >
                Вход
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'register'}
                className={mode === 'register' ? 'auth-tab active' : 'auth-tab'}
                onClick={() => setMode('register')}
              >
                Регистрация
              </button>
            </div>

            <h1>{mode === 'login' ? 'С возвращением' : 'Новое рабочее пространство'}</h1>
            <p className="auth-subtitle">
              {mode === 'login'
                ? 'Войдите, чтобы продолжить проверку карточек.'
                : 'Создайте рабочее пространство для своих товаров.'}
            </p>

            {(localError || error) && (
              <div className="alert alert-error" role="alert">
                <span className="alert-icon">
                  <IconInfo size={16} />
                </span>
                <div>{localError ?? error}</div>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="email">Электронная почта</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  autoComplete="email"
                  required
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="seller@example.com"
                />
              </div>

              <div className="field">
                <label htmlFor="password">Пароль</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  required
                  minLength={8}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Минимум 8 символов"
                />
              </div>

              {mode === 'register' && (
                <>
                  <div className="field">
                    <label htmlFor="displayName">Имя</label>
                    <input
                      id="displayName"
                      type="text"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      placeholder="Как к вам обращаться"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="workspaceName">Название рабочего пространства</label>
                    <input
                      id="workspaceName"
                      type="text"
                      value={workspaceName}
                      onChange={(event) => setWorkspaceName(event.target.value)}
                      placeholder="Например, «Карточки Wildberries»"
                    />
                  </div>
                </>
              )}

              <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
                {busy ? 'Выполняем…' : mode === 'login' ? 'Войти' : 'Создать пространство'}
                {!busy && <IconArrowRight size={16} />}
              </button>
            </form>

            <div className="auth-divider">
              <span>или</span>
            </div>

            <button
              type="button"
              className="btn btn-block"
              onClick={() => void handleDemo()}
              disabled={busy}
            >
              Войти в демонстрационном режиме
            </button>

            <p className="auth-note">
              Демо-пространство содержит синтетический товар с документами и отзывами. Все данные в нём
              вымышлены и явно помечены.
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}
