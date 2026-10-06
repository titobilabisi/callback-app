import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import TextField from '../components/TextField'
import { homePathFor, useAuth } from '../AuthContext'

export default function SignIn() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const user = await login(email, password)
      navigate(homePathFor(user), { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <AppHeader />
      <form onSubmit={submit} className="flex-1 flex flex-col">
        <h1 className="text-2xl font-semibold text-ink mb-1">Welcome back</h1>
        <p className="text-slate mb-6">Sign in to check a call.</p>
        <TextField label="Email" id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <TextField label="Password" id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-4">{error}</p>}
        <div className="flex-1" />
        <Button variant="primary" type="submit" disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</Button>
        <p className="text-center text-sm text-slate mt-4">
          New here? <Link to="/signup" className="text-teal font-medium underline">Create an account</Link>
        </p>
        <p className="text-center text-xs text-slate mt-2">
          Family members join with an invite link from the person they're helping.
        </p>
      </form>
    </Screen>
  )
}
