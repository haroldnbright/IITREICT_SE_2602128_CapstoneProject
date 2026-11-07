// Route guard that checks login and role before showing a page
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { HOME_BY_ROLE, useAuth } from '../context/AuthContext'

// Wrap routes with this to require login, and optionally a specific role.
// The backend checks roles too; this only keeps people out of pages they can't use.
export default function ProtectedRoute({ roles }) {
  const { user } = useAuth()
  const location = useLocation()

  // Remember the page they wanted so login can send them back there
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  // Wrong role goes to that role's own home page
  if (roles && !roles.includes(user.role)) return <Navigate to={HOME_BY_ROLE[user.role]} replace />
  // Allowed, so render the nested route
  return <Outlet />
}
