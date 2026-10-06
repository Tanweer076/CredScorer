import { Navigate } from 'react-router-dom'
import { homeFor, useAuth } from '../auth'

// Shows the page only to logged-in users with one of the given roles.
// The API checks roles too; this just keeps people out of screens they can't use.
export default function RequireRole({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="p-8 text-slate-500">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) return <Navigate to={homeFor(user)} replace />
  return children
}