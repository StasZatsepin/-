import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/', label: 'Обзор', icon: '◧', end: true },
  { to: '/products', label: 'Товары', icon: '▤', end: false },
  { to: '/checks', label: 'Проверки', icon: '✔', end: false },
  { to: '/history', label: 'История', icon: '↺', end: false },
  { to: '/settings', label: 'Настройки', icon: '⚙', end: false },
]

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            ПР
          </div>
          <div className="brand-text">
            <strong>Обещание против реальности</strong>
            <span>Проверка товарных утверждений</span>
          </div>
        </div>

        <nav className="nav" aria-label="Основная навигация">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <strong>{user?.workspace?.name ?? 'Рабочее пространство'}</strong>
          <div>{user?.email}</div>
          {user?.workspace?.is_demo && (
            <div style={{ marginTop: 6 }}>
              <span className="badge badge-medium">демо-режим</span>
            </div>
          )}
          <button type="button" className="btn btn-sm" style={{ marginTop: 10 }} onClick={handleLogout}>
            Выйти
          </button>
        </div>
      </aside>

      <div className="main">
        <Outlet />
      </div>
    </div>
  )
}
