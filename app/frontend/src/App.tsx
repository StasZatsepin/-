import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Loading } from './components/States'
import { useAuth } from './context/AuthContext'
import { ChecksPage } from './pages/ChecksPage'
import { HistoryPage } from './pages/HistoryPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'
import { OverviewPage } from './pages/OverviewPage'
import { ProductFormPage } from './pages/ProductFormPage'
import { ProductPage } from './pages/ProductPage'
import { ProductsPage } from './pages/ProductsPage'
import { ReportPage } from './pages/ReportPage'
import { SettingsPage } from './pages/SettingsPage'

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh' }}>
        <Loading label="Проверяем сессию…" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/app" element={<OverviewPage />} />
        <Route path="/app/products" element={<ProductsPage />} />
        <Route path="/app/products/new" element={<ProductFormPage />} />
        <Route path="/app/products/:productId" element={<ProductPage />} />
        <Route path="/app/products/:productId/edit" element={<ProductFormPage />} />
        <Route path="/app/products/:productId/report/:runId" element={<ReportPage />} />
        <Route path="/app/checks" element={<ChecksPage />} />
        <Route path="/app/history" element={<HistoryPage />} />
        <Route path="/app/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
