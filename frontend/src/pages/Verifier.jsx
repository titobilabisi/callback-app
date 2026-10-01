import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import Button from '../components/Button'
import { RISK_QUESTIONS, useCheck } from '../CheckContext'

const LABELS = {
  money: 'Asking for money or gift cards',
  secrecy: 'Asked to keep it secret',
  urgency: 'Said to act right now',
  unusualContact: 'Unknown number',
}

export default function Verifier() {
  const navigate = useNavigate()
  const { answers } = useCheck()

  const summary = RISK_QUESTIONS.map((q) => ({
    key: q.key,
    label: LABELS[q.key],
    value: answers[q.key],
  }))

  function respond() {
    navigate('/home')
  }

  return (
    <Screen>
      <AppHeader />
      <div className="bg-teal-light rounded-2xl p-4 mb-4">
        <p className="text-teal text-sm font-medium mb-1">Needs your help</p>
        <p className="text-ink">Margaret is asking you to check a call.</p>
      </div>

      <div className="border border-black/10 rounded-2xl p-4 mb-6">
        <p className="text-ink font-medium mb-3">Call summary</p>
        <div className="space-y-3">
          {summary.map((row) => (
            <div key={row.key} className="flex items-center justify-between text-sm">
              <span className="text-ink">{row.label}</span>
              <span className={`px-3 py-1 rounded-full ${row.value ? 'bg-danger-bg text-danger-ink' : 'bg-success-bg text-success-ink'}`}>
                {row.value === undefined ? 'n/a' : row.value ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1" />
      <div className="space-y-3">
        <Button variant="choice" onClick={respond}>Approve</Button>
        <Button variant="choice" onClick={respond}>Decline</Button>
      </div>
    </Screen>
  )
}
