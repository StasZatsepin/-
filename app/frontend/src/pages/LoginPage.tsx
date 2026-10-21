import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

type Mode = 'login' | 'register'

export function LoginPage() {
  const { user, login, register, enterDemo, error } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [workspaceName, setWorkspaceName] = useState('')
  const [busy, setBusy] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const navigate = useNavigate()

  if (user) {
    return <Navigate to="/" replace />
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
      navigate('/')
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Не удалось выполнить вход')
    } finally {
      setBusy(false)
    }
  }

  async function handleDemo() {
    setBusy(true)
    setLocalError(null)
    try {
      await enterDemo()
      navigate('/')
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Демо-режим недоступен')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Обещание против реальности</h1>
        <p className="auth-subtitle">
          Доказательная проверка карточек товаров: сопоставляем заявления, характеристики,
          документы и отзывы.
        </p>

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

        {(localError || error) && (
          <div className="alert alert-error" role="alert">
            {localError ?? error}
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
          </button>
        </form>

        <div className="divider">или</div>

        <button type="button" className="btn btn-block" onClick={() => void handleDemo()} disabled={busy}>
          Войти в демонстрационном режиме
        </button>

        <div className="demo-note">
          Демо-режим открывает рабочее пространство с синтетическим примером товара.
          Все данные в нём вымышлены и явно помечены. Внешние сервисы и платные API не
          используются.
        </div>
      </div>
    </div>
  )
}
