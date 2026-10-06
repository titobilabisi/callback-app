import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import IconTile from '../components/IconTile'
import { api } from '../api'
import { useCheck } from '../CheckContext'

const POLL_MS = 2000

const RESULT_PATH = {
  verified: '/result/approved',
  denied: '/result/denied',
  unable_to_verify: '/result/timeout',
}

// Asks the server every couple of seconds whether the family has answered.
// The result shown is whatever the server says; nothing here decides it.
export default function Waiting() {
  const navigate = useNavigate()
  const { requestId, lastRequest, updateRequest } = useCheck()
  const [trouble, setTrouble] = useState(false)

  useEffect(() => {
    if (!requestId) {
      navigate('/home', { replace: true })
      return undefined
    }

    let cancelled = false
    let timer

    async function poll() {
      try {
        const req = await api(`/requests/${requestId}`)
        if (cancelled) return
        setTrouble(false)
        updateRequest(req)
        const path = RESULT_PATH[req.status]
        if (path) {
          navigate(path, { replace: true })
          return
        }
      } catch (err) {
        if (cancelled) return
        if (err.status === 401) {
          navigate('/signin', { replace: true })
          return
        }
        if (err.status === 404) {
          navigate('/home', { replace: true })
          return
        }
        setTrouble(true)
      }
      timer = setTimeout(poll, POLL_MS)
    }

    poll()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [requestId, navigate, updateRequest])

  const needsTwo = lastRequest?.required_approvals === 2
  const minutesLeft = lastRequest?.seconds_left ? Math.ceil(lastRequest.seconds_left / 60) : null

  return (
    <Screen>
      <AppHeader />
      <div className="flex-1 flex flex-col items-center justify-center text-center">
        <IconTile tone="teal">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        </IconTile>
        <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">Just a minute...</h1>
        <p className="text-slate">
          {needsTwo
            ? `We're checking with your family. ${lastRequest.approvals} of ${lastRequest.required_approvals} have approved.`
            : "We're checking with your family."}
        </p>
        {minutesLeft && <p className="text-slate text-sm mt-2">We'll wait about {minutesLeft} more {minutesLeft === 1 ? 'minute' : 'minutes'}.</p>}
      </div>

      {lastRequest?.can_be_completed === false && (
        <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-3">
          This call needs two family members, but only one has joined. Don't send anything. Ask another family member to join.
        </p>
      )}
      {trouble && (
        <p role="status" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-3">
          Having trouble connecting. Still trying...
        </p>
      )}

      <div className="bg-teal-light text-teal rounded-2xl py-3 text-center text-sm">
        Stay on this screen
      </div>
    </Screen>
  )
}
