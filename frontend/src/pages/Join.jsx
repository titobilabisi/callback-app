import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import TextField from '../components/TextField'
import { api } from '../api'
import { useAuth } from '../AuthContext'

// A family member's only way in: an invite link from the elder. The server
// refuses any sign up without a valid, unused, unexpired invite.
export default function Join() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api('/verifiers', { method: 'POST', body: { invite_token: token, name, email, password } })
      await login(email, password)
      navigate('/verify', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <AppHeader />
      <form onSubmit={submit} className="flex-1 flex flex-col">
        <h1 className="text-2xl font-semibold text-ink mb-1">You've been invited</h1>
        <p className="text-slate mb-6">A family member asked you to help them check suspicious calls. Create your account to join.</p>
        <TextField label="Your name" id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required />
        <TextField label="Email" id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <TextField label="Password (at least 8 characters)" id="password" type="password" autoComplete="new-password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-4">{error}</p>}
        <div className="flex-1" />
        <Button variant="primary" type="submit" disabled={busy}>{busy ? 'Joining...' : 'Join'}</Button>
        <p className="text-center text-sm text-slate mt-4">
          Already joined? <Link to="/signin" className="text-teal font-medium underline">Sign in</Link>
        </p>
      </form>
    </Screen>
  )
}
