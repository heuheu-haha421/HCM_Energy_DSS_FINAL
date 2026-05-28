import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import { authService } from './services/authService'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ScenarioPage from './pages/ScenarioPage'
import AIMonitorPage from './pages/AIMonitorPage'
import DataManagerPage from './pages/DataManagerPage'
import Layout from './components/common/Layout'
import { isAdminOrDev } from './utils/roles'

function readJwtPayload(token) {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), '=')
    return JSON.parse(atob(padded))
  } catch {
    return null
  }
}

function ProtectedRoute({ children, adminOnly = false }) {
  const { token, user } = useAuthStore()
  if (!token) return <Navigate to="/login" replace />
  if (adminOnly && !isAdminOrDev(user)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const { token, user, setUser, logout } = useAuthStore()

  useEffect(() => {
    if (!token) return

    const tokenUser = readJwtPayload(token)
    authService.me()
      .then(data => setUser({ ...tokenUser, ...user, ...data }))
      .catch((error) => {
        if (error?.status === 401 || error?.status === 403) {
          logout()
        }
      })
  }, [token, setUser, logout])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={
          <ProtectedRoute><Layout /></ProtectedRoute>
        }>
          <Route index element={<DashboardPage />} />
          <Route path="scenarios" element={<ScenarioPage />} />
          <Route path="ai-monitor" element={<AIMonitorPage />} />
          <Route path="data" element={<DataManagerPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
