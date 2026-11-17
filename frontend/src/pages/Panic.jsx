import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import IconTile from '../components/IconTile'
import Button from '../components/Button'
import { api } from '../api'

// The panic alert. Opening this screen sends the alert, so it is one tap
// from the home screen. The server only ever sends it to this person's own
// family.
export default function Panic() {
  const navigate = useNavigate()
  const [state, setState] = useState({ status: 'sending', notified: 0, error: '' })
  const sent = useRef(false)

  async function send() {
    setState({ status: 'sending', notified: 0, error: '' })
    try {
      const res = await api('/panic', { method: 'POST' })
      setState({ status: 'sent', notified: res.notified, error: '' })
    } catch (err) {
      if (err.status === 401) navigate('/signin', { replace: true })
      else setState({ status: 'failed', notified: 0, error: err.message })
    }
  }

  useEffect(() => {
    if (sent.current) return
    sent.current = true
    send()
  }, [])

  return (
    <Screen>
      <AppHeader />
      <div className="flex-1 flex flex-col items-center text-center">
        <IconTile tone={state.status === 'failed' ? 'danger' : 'teal'}>
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.7 21a2 2 0 0 1-3.4 0" />
          </svg>
        </IconTile>

        {state.status === 'sending' && (
          <h1 className="text-2xl font-semibold text-ink mt-6">Telling your family...</h1>
        )}

        {state.status === 'sent' && (
          <>
            <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">
              {state.notified > 0 ? 'Your family has been told' : 'No family to tell yet'}
            </h1>
            <p className="text-slate mb-6">
              {state.notified > 0
                ? 'They can see you need help right now.'
                : 'Add a family member so they can be reached next time.'}
            </p>
            <div className="w-full bg-teal-light text-teal rounded-2xl p-4 text-sm text-left space-y-2">
              <p>Hang up the phone. You can always do that.</p>
              <p>Do not send money or share any codes.</p>
              <p>Wait for a family member to call you.</p>
            </div>
          </>
        )}

        {state.status === 'failed' && (
          <>
            <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">The alert did not go through</h1>
            <p role="alert" className="text-danger-ink mb-4">{state.error}</p>
            <p className="text-slate text-sm">Hang up and call someone you trust directly.</p>
          </>
        )}
      </div>
      <div className="space-y-3">
        {state.status === 'failed' && <Button variant="primary" onClick={send}>Try again</Button>}
        <Button variant={state.status === 'failed' ? 'choice' : 'primary'} onClick={() => navigate('/home')}>Back to home</Button>
      </div>
    </Screen>
  )
}
