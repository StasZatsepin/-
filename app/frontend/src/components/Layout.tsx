import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LogoMark, LogoWordmark } from './Logo'
import {
  IconChecks,
  IconClose,
  IconHistory,
  IconLogout,
  IconMenu,
  IconOverview,
  IconProducts,
  IconSettings,
} from './icons'
import { StorageBanner } from './StorageBanner'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/app', label: 'Обзор', icon: IconOverview, end: true },
  { to: '/app/products', label: 'Товары', icon: IconProducts, end: false },
  { to: '/app/checks', label: 'Проверки', icon: IconChecks, end: false },
  { to: '/app/history', label: 'История', icon: IconHistory, end: false },
  { to: '/app/settings', label: 'Настройки', icon: IconSettings, end: false },
]

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const toggleRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  // Пока меню открыто: Esc закрывает его, фон под панелью не прокручивается.
  useEffect(() => {
    if (!menuOpen) return undefined
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMenuOpen(false)
        toggleRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [menuOpen])

  function handleMenuToggle() {
    setMenuOpen((prev) => !prev)
  }

  function handleMenuClose() {
    setMenuOpen(false)
    toggleRef.current?.focus()
  }

  function handleLogout() {
    logout()
    navigate('/app', { replace: true })
  }

  const initials = (user?.display_name || user?.email || 'П')
    .slice(0, 1)
    .toUpperCase()

  return (
    <div className="app-shell">
      {menuOpen && (
        <div
          className="sidebar-backdrop"
          role="presentation"
          onClick={handleMenuClose}
        />
      )}

      <aside id="app-sidebar" className={menuOpen ? 'sidebar is-open' : 'sidebar'}>
        <div className="sidebar-header">
          <NavLink to="/app" className="sidebar-brand">
            <LogoMark size={32} variant="dark" />
            <LogoWordmark variant="dark" compact />
          </NavLink>
          <button
            type="button"
            className="sidebar-close"
            onClick={handleMenuClose}
            aria-label="Закрыть навигацию"
          >
            <IconClose size={20} />
          </button>
        </div>

        <div>
          <div className="sidebar-section-label">Рабочее пространство</div>
          <nav className="nav" aria-label="Основная навигация" style={{ marginTop: 8 }}>
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  <span className="nav-icon">
                    <Icon size={18} />
                  </span>
                  <span>{item.label}</span>
                </NavLink>
              )
            })}
          </nav>
        </div>

        <div className="sidebar-footer">
          <div className="workspace-card">
            <strong>{user?.workspace?.name ?? 'Рабочее пространство'}</strong>
            <span>{user?.workspace?.is_demo ? 'Демонстрационные данные' : 'Рабочие данные'}</span>
          </div>
          <div className="sidebar-user">
            <span className="avatar" aria-hidden="true">
              {initials}
            </span>
            <span className="sidebar-user-meta">
              <strong>{user?.display_name || 'Пользователь'}</strong>
              <span>{user?.email}</span>
            </span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ color: 'var(--text-inverse-2)', padding: 10, minWidth: 44 }}
              onClick={handleLogout}
              aria-label="Выйти из рабочего пространства"
              title="Выйти"
            >
              <IconLogout size={17} />
            </button>
          </div>
        </div>
      </aside>

      <div className="main">
        <div className="mobile-bar">
          <button
            ref={toggleRef}
            type="button"
            className="mobile-nav-toggle"
            onClick={handleMenuToggle}
            aria-label={menuOpen ? 'Закрыть навигацию' : 'Открыть навигацию'}
            aria-expanded={menuOpen}
            aria-controls="app-sidebar"
          >
            <IconMenu size={22} />
          </button>
          <NavLink to="/app" className="mobile-bar-brand" aria-label="На главную страницу рабочего пространства">
            <LogoMark size={28} />
            <span>Обещание против реальности</span>
          </NavLink>
        </div>

        <StorageBanner />
        <Outlet />
      </div>

      <nav className="bottom-nav" aria-label="Быстрая навигация">
        {NAV_ITEMS.slice(0, 4).map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'bottom-nav-link active' : 'bottom-nav-link')}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}
