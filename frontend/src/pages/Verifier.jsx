import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import IconTile from '../components/IconTile'
import Button from '../components/Button'
import { api } from '../api'
import { useAuth } from '../AuthContext'

const POLL_MS = 3000

// The family member's screen. It lists calls that someone they help has
// asked to have checked, and sends their approve or decline to the server.
export default function Verifier() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [inbox, setInbox] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState('')

  const load = useCallback(async () => {
    try {
      setInbox(await api('/verifier/requests'))
      setError('')
    } catch (err) {
      if (err.status === 401) navigate('/signin', { replace: true })
      else setError(err.message)
    }
  }, [navigate])

  useEffect(() => {
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  async function respond(req, decision) {
    setBusy(true)
    setError('')
    try {
      await api(`/requests/${req.id}/respond`, { method: 'POST', body: { decision } })
      setSent(decision)
    } catch (err) {
      // For example the request already finished or ran out of time.
      setError(err.message)
      setSent('')
    } finally {
      setBusy(false)
      load()
    }
  }

  async function signOut() {
    await logout()
    navigate('/signin', { replace: true })
  }

  const current = inbox && inbox.length > 0 ? inbox[0] : null

  return (
    <Screen>
      <AppHeader />

      {sent && (
        <p role="status" className="bg-success-bg text-success-ink rounded-2xl p-3 text-sm mb-4">
          {sent === 'approve' ? 'Thanks. Your approval was sent.' : 'Thanks. Your answer was sent.'}
        </p>
      )}
      {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-4">{error}</p>}

      {!current ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center">
          <IconTile tone="teal">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12l2 2 4-4" />
              <circle cx="12" cy="12" r="10" />
            </svg>
          </IconTile>
          <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">Nothing needs your help</h1>
          <p className="text-slate">
            {inbox === null ? 'Checking...' : "When someone asks you to check a call, it'll show up here."}
          </p>
        </div>
      ) : (
        <>
          <div className="bg-teal-light rounded-2xl p-4 mb-4">
            <p className="text-teal text-sm font-medium mb-1">Needs your help</p>
            <p className="text-ink">{current.elder_name} is asking you to check a call.</p>
            {inbox.length > 1 && <p className="text-slate text-sm mt-1">{inbox.length - 1} more waiting after this one.</p>}
          </div>

          {current.caller_note && (
            <div className="border border-black/10 rounded-2xl p-4 mb-4">
              <p className="text-slate text-sm mb-1">The caller said</p>
              <p className="text-ink">{current.caller_note}</p>
            </div>
          )}

          <div className="border border-black/10 rounded-2xl p-4 mb-4">
            <p className="text-ink font-medium mb-3">Call summary</p>
            <div className="space-y-3">
              {current.summary.map((row) => (
                <div key={row.key} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-ink">{row.label}</span>
                  <span className={`px-3 py-1 rounded-full shrink-0 ${row.value ? 'bg-danger-bg text-danger-ink' : 'bg-success-bg text-success-ink'}`}>
                    {row.value ? 'Yes' : 'No'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {current.required_approvals === 2 && (
            <p className="bg-teal-light text-teal rounded-2xl p-3 text-sm mb-4">
              This call involves money or personal info, so two family members need to approve it. {current.approvals} of 2 so far.
            </p>
          )}

          <div className="flex-1" />
          <div className="space-y-3">
            <Button variant="choice" onClick={() => respond(current, 'approve')} disabled={busy}>Approve</Button>
            <Button variant="choice" onClick={() => respond(current, 'decline')} disabled={busy}>Decline</Button>
          </div>
        </>
      )}

      <div className="text-center text-xs text-slate mt-4">
        Signed in as {user?.name}.{' '}
        <button type="button" onClick={signOut} className="text-teal underline">Sign out</button>
      </div>
    </Screen>
  )
}
