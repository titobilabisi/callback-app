import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './api'

// Who is logged in. The server is the source of truth: on load we ask it
// (GET /api/me) rather than trusting anything stored in the browser.
const AuthContext = createContext(null)

export function homePathFor(user) {
  return user?.role === 'verifier' ? '/verify' : '/home'
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api('/me')
      .then((u) => !cancelled && setUser(u))
      .catch(() => !cancelled && setUser(null))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const u = await api('/login', { method: 'POST', body: { email, password } })
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    try {
      await api('/logout', { method: 'POST' })
    } finally {
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
