import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { isAdminOrDev } from '../../utils/roles'

/**
 * Props:
 *   adminOnly – boolean, redirect non-admins to /
 *   children  – React node
 */
export default function ProtectedRoute({ children, adminOnly = false }) {
  const { token, user } = useAuthStore()
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (adminOnly && !isAdminOrDev(user)) {
    return <Navigate to="/" replace />
  }

  return children
}
