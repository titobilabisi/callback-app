import { useNavigate, useParams } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import ProgressBar from '../components/ProgressBar'
import IconTile from '../components/IconTile'
import Button from '../components/Button'
import { RISK_QUESTIONS, useCheck } from '../CheckContext'

export default function RiskQuestion() {
  const { step } = useParams()
  const stepNum = Number(step)
  const navigate = useNavigate()
  const { answer } = useCheck()

  const question = RISK_QUESTIONS[stepNum - 1]
  if (!question) {
    navigate('/home')
    return null
  }

  function choose(value) {
    answer(question.key, value)
    if (stepNum < RISK_QUESTIONS.length) {
      navigate(`/check/${stepNum + 1}`)
    } else {
      navigate('/waiting')
    }
  }

  return (
    <Screen>
      <AppHeader />
      <ProgressBar step={stepNum} total={RISK_QUESTIONS.length} />
      <div className="flex-1 flex flex-col items-center text-center">
        <IconTile tone="teal">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M15 9l-6 6M9 9l6 6" />
          </svg>
        </IconTile>
        <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">{question.text}</h1>
        <p className="text-slate">Choose the answer that fits best.</p>
      </div>
      <div className="space-y-3">
        <Button variant="choice" onClick={() => choose(true)}>Yes</Button>
        <Button variant="choice" onClick={() => choose(false)}>No</Button>
      </div>
    </Screen>
  )
}
