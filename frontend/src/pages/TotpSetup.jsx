import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import TextField from '../components/TextField'
import { api } from '../api'
import { useAuth } from '../AuthContext'

// One-time setup for a family member: add CallBack to an authenticator
// app, then prove it works by typing the current code. Approving a call
// needs a code from this app, so a stolen password alone cannot approve.
export default function TotpSetup() {
  const navigate = useNavigate()
  const { refresh } = useAuth()
  const [setup, setSetup] = useState(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    api('/verifier/totp')
      .then((s) => {
        if (cancelled) return
        if (s.confirmed) navigate('/verify', { replace: true })
        else setSetup(s)
      })
      .catch((err) => !cancelled && setError(err.message))
    return () => {
      cancelled = true
    }
  }, [navigate])

  async function confirm(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api('/verifier/totp/confirm', { method: 'POST', body: { code } })
      await refresh()
      navigate('/verify', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <AppHeader />
      <form onSubmit={confirm} className="flex-1 flex flex-col">
        <h1 className="text-2xl font-semibold text-ink mb-1">Set up your approval codes</h1>
        <p className="text-slate mb-4">
          To approve a call you will type a 6 digit code from an authenticator app (like Google Authenticator).
        </p>

        {setup && (
          <div className="border border-black/10 rounded-2xl p-4 mb-4 text-center">
            <p className="text-sm text-ink mb-3">1. In your app, add an account by scanning this:</p>
            <div className="inline-block bg-white p-3 rounded-xl">
              <QRCodeSVG value={setup.uri} size={160} />
            </div>
            <p className="text-xs text-slate mt-3">Can't scan? Enter this key instead:</p>
            <p className="font-mono text-sm text-ink break-all select-all mt-1">{setup.secret}</p>
          </div>
        )}

        <p className="text-sm text-ink mb-2">2. Type the 6 digit code your app shows now:</p>
        <TextField
          label="Code"
          id="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          pattern="[0-9]{6}"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          required
        />
        {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-4">{error}</p>}
        <div className="flex-1" />
        <Button variant="primary" type="submit" disabled={busy || code.length !== 6}>
          {busy ? 'Checking...' : 'Finish setup'}
        </Button>
      </form>
    </Screen>
  )
}
