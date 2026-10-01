import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import StatusPill from '../components/StatusPill'
import IconTile from '../components/IconTile'
import Button from '../components/Button'

export default function Timeout() {
  const navigate = useNavigate()

  return (
    <Screen>
      <AppHeader />
      <div className="flex-1 flex flex-col items-center text-center">
        <StatusPill tone="teal">Still waiting</StatusPill>
        <IconTile tone="teal">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
        </IconTile>
        <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">We couldn't reach your family yet.</h1>
        <p className="text-slate">Don't send anything, try again soon.</p>
      </div>
      <Button variant="primary" onClick={() => navigate('/waiting')}>Try again</Button>
    </Screen>
  )
}
