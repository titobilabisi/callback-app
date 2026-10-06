import { Navigate } from 'react-router-dom'
import { homePathFor, useAuth } from '../AuthContext'

// Keeps a screen for one role only. This is a convenience for the person
// using the app; the real access check is always made again by the server.
export default function Protected({ role, children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/signin" replace />
  if (user.role !== role) return <Navigate to={homePathFor(user)} replace />
  return children
}
