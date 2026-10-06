import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import { api } from '../api'
import { useAuth } from '../AuthContext'

// The elder's family circle: who is enrolled, and a way to invite more.
// Invites are single use and expire, and each one is created by the elder.
export default function Family() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [verifiers, setVerifiers] = useState([])
  const [inviteLink, setInviteLink] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    try {
      setVerifiers(await api(`/elders/${user.id}/verifiers`))
    } catch (err) {
      setError(err.message)
    }
  }, [user.id])

  // Refresh every few seconds so a family member who just joined shows up
  // without the page being reloaded.
  useEffect(() => {
    load()
    const timer = setInterval(load, 4000)
    return () => clearInterval(timer)
  }, [load])

  async function createInvite() {
    setBusy(true)
    setError('')
    setCopied(false)
    // Clear the previous link right away so a used, stale link is never
    // shown next to a "new invite" button.
    setInviteLink('')
    try {
      const invite = await api(`/elders/${user.id}/invites`, { method: 'POST', body: {} })
      setInviteLink(`${window.location.origin}/join/${invite.token}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(inviteLink)
      setCopied(true)
    } catch {
      // Clipboard needs a secure page; the link is also shown in a box
      // that can be selected by hand.
    }
  }

  return (
    <Screen>
      <AppHeader />
      <h1 className="text-2xl font-semibold text-ink mb-1">My family</h1>
      <p className="text-slate mb-5">The people who can help you check a call.</p>

      <div className="border border-black/10 rounded-2xl p-4 mb-4">
        {verifiers.length === 0 ? (
          <p className="text-slate text-sm">No one yet. Invite a family member below.</p>
        ) : (
          <ul className="space-y-2">
            {verifiers.map((v) => (
              <li key={v.id} className="flex items-center justify-between text-ink">
                <span>{v.name}</span>
                <span className="text-xs px-3 py-1 rounded-full bg-success-bg text-success-ink">Joined</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {verifiers.length === 1 && (
        <p className="bg-teal-light text-teal rounded-2xl p-3 text-sm mb-4">
          Add a second person. Calls that involve money or personal info need two family members to approve.
        </p>
      )}

      {inviteLink && (
        <div className="mb-4">
          <p className="text-sm font-medium text-ink mb-1.5">Send this link to one person (good for 3 days, works once)</p>
          <input
            readOnly
            value={inviteLink}
            onFocus={(e) => e.target.select()}
            aria-label="Invite link"
            className="w-full rounded-2xl border-2 border-black/10 bg-white px-3 py-3 text-xs text-ink"
          />
          <button type="button" onClick={copy} className="mt-2 text-sm text-teal font-medium underline">
            {copied ? 'Copied' : 'Copy link'}
          </button>
        </div>
      )}

      {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-4">{error}</p>}

      <div className="flex-1" />
      <div className="space-y-3">
        <Button variant="choice" onClick={createInvite} disabled={busy}>
          {busy ? 'Making link...' : 'Invite a family member'}
        </Button>
        <Button variant="primary" onClick={() => navigate('/home')}>Done</Button>
      </div>
    </Screen>
  )
}
