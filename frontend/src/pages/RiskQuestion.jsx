import { useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import ProgressBar from '../components/ProgressBar'
import IconTile from '../components/IconTile'
import Button from '../components/Button'
import { useCheck } from '../CheckContext'

export default function RiskQuestion() {
  const { step } = useParams()
  const stepNum = Number(step)
  const navigate = useNavigate()
  const { questions, questionsError, answers, answer, submit } = useCheck()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (questionsError) {
    return (
      <Screen>
        <AppHeader />
        <p role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm">{questionsError}</p>
      </Screen>
    )
  }
  if (!questions) return <Screen><AppHeader /></Screen>

  const question = questions[stepNum - 1]
  if (!question) return <Navigate to="/home" replace />

  // Arriving on a later question without having answered the earlier ones
  // (a bookmark, a refresh) starts over rather than sending a partial check.
  const skipped = questions.slice(0, stepNum - 1).some((q) => answers[q.key] === undefined)
  if (skipped) return <Navigate to="/check/1" replace />

  async function choose(value) {
    answer(question.key, value)
    if (stepNum < questions.length) {
      navigate(`/check/${stepNum + 1}`)
      return
    }
    setBusy(true)
    setError(null)
    try {
      await submit({ ...answers, [question.key]: value })
      navigate('/waiting', { replace: true })
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <AppHeader />
      <ProgressBar step={stepNum} total={questions.length} />
      <div className="flex-1 flex flex-col items-center text-center">
        <IconTile tone="teal">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
        </IconTile>
        <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">{question.text}</h1>
        <p className="text-slate">Choose the answer that fits best.</p>
      </div>

      {error && (
        <div role="alert" className="bg-danger-bg text-danger-ink rounded-2xl p-3 text-sm mb-3">
          {error.message}
          {error.status === 409 && (
            <button type="button" onClick={() => navigate('/family')} className="block mt-2 font-medium underline">
              Go to my family
            </button>
          )}
        </div>
      )}

      <div className="space-y-3">
        <Button variant="choice" onClick={() => choose(true)} disabled={busy}>Yes</Button>
        <Button variant="choice" onClick={() => choose(false)} disabled={busy}>No</Button>
        {stepNum > 1 && (
          <button type="button" onClick={() => navigate(-1)} disabled={busy} className="w-full text-sm text-slate py-2">
            Back
          </button>
        )}
      </div>
    </Screen>
  )
}
