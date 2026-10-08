import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import { useCheck } from '../CheckContext'

const MAX = 140

// Last step before sending: an optional note about who the caller said
// they were, so family can decide without calling back.
export default function CallerNote() {
  const navigate = useNavigate()
  const { questions, answers, submit } = useCheck()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (!questions) return <Screen><AppHeader /></Screen>
  // Opened without finishing the questions (a bookmark, a refresh): start over.
  if (questions.some((q) => answers[q.key] === undefined)) return <Navigate to="/check/1" replace />

  async function send(text) {
    setBusy(true)
    setError(null)
    try {
      await submit(answers, text)
      navigate('/waiting', { replace: true })
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <AppHeader />
      <div className="flex-1">
        <h1 className="text-2xl font-semibold text-ink mb-2">Who did the caller say they were?</h1>
        <p className="text-slate mb-6">Optional. A few words help your family decide faster.</p>
        <label htmlFor="caller-note" className="block text-sm font-medium text-ink mb-1.5">
          Short note
        </label>
        <textarea
          id="caller-note"
          rows={3}
          maxLength={MAX}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="For example: says he is from my insurance"
          className="w-full rounded-2xl border-2 border-black/10 bg-white px-4 py-3.5 text-base text-ink focus:outline-none focus:border-teal"
        />
        <p className="text-xs text-slate mt-1 text-right">{note.length} of {MAX}</p>
      </div>

      {error && <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-3">{error.message}</p>}

      <div className="space-y-3">
        <Button onClick={() => send(note)} disabled={busy}>Send to my family</Button>
        <Button variant="choice" onClick={() => send('')} disabled={busy}>Skip</Button>
      </div>
    </Screen>
  )
}
