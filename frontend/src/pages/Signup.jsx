import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import TextField from '../components/TextField'
import { api } from '../api'
import { useAuth } from '../AuthContext'

// Only the person who gets the suspicious calls signs up on their own.
// Family members can only join through an invite (see Join.jsx).
export default function Signup() {
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
      await api('/elders', { method: 'POST', body: { name, email, password } })
      await login(email, password)
      navigate('/family', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <AppHeader />
      <form onSubmit={submit} className="flex-1 flex flex-col">
        <h1 className="text-2xl font-semibold text-ink mb-1">Create your account</h1>
        <p className="text-slate mb-6">Next, you'll invite a family member to help you check calls.</p>
        <TextField label="Your name" id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required />
        <TextField label="Email" id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <TextField label="Password (at least 8 characters)" id="password" type="password" autoComplete="new-password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-4">{error}</p>}
        <div className="flex-1" />
        <Button variant="primary" type="submit" disabled={busy}>{busy ? 'Creating...' : 'Create account'}</Button>
        <p className="text-center text-sm text-slate mt-4">
          Already have one? <Link to="/signin" className="text-teal font-medium underline">Sign in</Link>
        </p>
      </form>
    </Screen>
  )
}
