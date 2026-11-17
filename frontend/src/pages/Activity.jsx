import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import StatusPill from '../components/StatusPill'
import { api } from '../api'

// Plain-language reasons for a refused answer or invite.
const REASONS = {
  bad_or_reused_code: 'the code was wrong or already used',
  duplicate_response: 'they had already answered',
  expired: 'it was too late',
  authenticator_not_set_up: 'their authenticator app is not set up',
  not_enrolled_for_this_person: 'they are not in your family',
  already_finished: 'the check was already finished',
  request_not_found: 'that check does not exist',
  invalid_decision: 'the answer was not valid',
  not_found: 'the link was not recognized',
  already_used: 'the link was already used',
  not_your_family: 'it was for a different family',
  wrong_password: 'wrong password',
  unknown_email: 'an unknown email',
  no_family_enrolled: 'no family members have joined yet',
  invalid_answers: 'the answers were not valid',
  invalid_note: 'the note was not valid',
}

const RESULTS = {
  verified: 'Check finished: approved',
  denied: 'Check finished: not approved',
  unable_to_verify: 'Check ran out of time',
}

// One short sentence per event, written for an older adult, not a log.
function describe(e) {
  const who = e.actor_name || 'Someone'
  const why = REASONS[e.detail?.reason]
  const because = why ? ` (${why})` : ''
  switch (e.event_type) {
    case 'elder_created': return 'You created your account'
    case 'invite_created': return 'You made an invite link'
    case 'invite_rejected': return `An invite link was refused${because}`
    case 'verifier_enrolled': return `${who} joined your family`
    case 'totp_confirmed': return `${who} set up their authenticator app`
    case 'totp_confirm_failed': return `${who} entered a wrong setup code`
    case 'login_success': return `${who} signed in`
    case 'login_failed': return `A sign in did not work${because}`
    case 'logout': return `${who} signed out`
    case 'access_denied': return 'Someone tried something they are not allowed to do'
    case 'rate_limited': return 'Too many tries, so it was paused for a few minutes'
    case 'request_created':
      return e.detail?.required_approvals === 2
        ? 'You asked for a check (needs 2 family members)'
        : 'You asked for a check (needs 1 family member)'
    case 'request_rejected': return `Your check could not start${because}`
    case 'response_approved': return `${who} approved your check`
    case 'response_declined': return `${who} declined your check`
    case 'response_rejected': return `${who}'s answer was not accepted${because}`
    case 'request_resolved': return RESULTS[e.detail?.status] || 'Check finished'
    case 'panic_raised': return `You sent a panic alert (${e.detail?.notified ?? 0} family told)`
    case 'panic_repeated': return 'You pressed the panic alert again while one was open'
    case 'panic_handled': return `${who} said they are handling your alert`
    case 'panic_rejected': return `${who} tried to open an alert that was not theirs`
    default: return 'Something happened'
  }
}

function when(iso) {
  // Times are stored in UTC without a zone marker, so add one before showing
  // them in the viewer's own time.
  const d = new Date(`${iso}Z`)
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

// The elder's activity: what happened on their account and their family's,
// including refused attempts. Read only.
export default function Activity() {
  const navigate = useNavigate()
  const [events, setEvents] = useState(null)
  const [intact, setIntact] = useState(null)
  const [onlyProblems, setOnlyProblems] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const [list, check] = await Promise.all([api('/audit'), api('/audit/verify')])
      setEvents(list)
      setIntact(check.intact)
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [load])

  const shown = (events || []).filter((e) => !onlyProblems || e.outcome === 'rejected')
  const problems = (events || []).filter((e) => e.outcome === 'rejected').length

  return (
    <Screen>
      <AppHeader />
      <h1 className="text-2xl font-semibold text-ink mb-1">Activity</h1>
      <p className="text-slate mb-4">What has happened on your account and with your family.</p>

      {intact !== null && (
        <div className="mb-4">
          <StatusPill tone={intact ? 'success' : 'danger'}>
            {intact ? 'Record looks untouched' : 'This record may have been changed'}
          </StatusPill>
        </div>
      )}

      <div className="flex gap-2 mb-4" role="group" aria-label="Filter activity">
        <button
          type="button"
          onClick={() => setOnlyProblems(false)}
          aria-pressed={!onlyProblems}
          className={`px-4 py-2 rounded-full text-sm font-medium ${!onlyProblems ? 'bg-teal text-white' : 'bg-teal-light text-teal'}`}
        >
          Everything
        </button>
        <button
          type="button"
          onClick={() => setOnlyProblems(true)}
          aria-pressed={onlyProblems}
          className={`px-4 py-2 rounded-full text-sm font-medium ${onlyProblems ? 'bg-teal text-white' : 'bg-teal-light text-teal'}`}
        >
          Problems ({problems})
        </button>
      </div>

      {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-4">{error}</p>}

      {events === null && !error && <p className="text-slate text-sm">Loading...</p>}
      {events !== null && shown.length === 0 && (
        <p className="text-slate text-sm">{onlyProblems ? 'No problems. That is a good sign.' : 'Nothing yet.'}</p>
      )}

      <ul className="space-y-2 mb-4">
        {shown.map((e) => (
          <li
            key={e.id}
            className={`rounded-2xl p-3 border ${e.outcome === 'rejected' ? 'bg-danger-bg border-danger/20' : 'border-black/10'}`}
          >
            <p className={`text-sm font-medium ${e.outcome === 'rejected' ? 'text-danger-ink' : 'text-ink'}`}>{describe(e)}</p>
            <p className="text-xs text-slate mt-0.5">{when(e.created_at)}</p>
          </li>
        ))}
      </ul>

      <div className="flex-1" />
      <Button variant="primary" onClick={() => navigate('/home')}>Back</Button>
    </Screen>
  )
}
