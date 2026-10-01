import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import StatusPill from '../components/StatusPill'
import IconTile from '../components/IconTile'
import Button from '../components/Button'

export default function Denied() {
  const navigate = useNavigate()

  return (
    <Screen>
      <AppHeader />
      <div className="flex-1 flex flex-col items-center text-center">
        <StatusPill tone="danger">Call declined</StatusPill>
        <IconTile tone="danger">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45c.84.3 1.75.46 2.69.46a2 2 0 0 1 2 2V20a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3.75a2 2 0 0 1 2 2c0 .94.16 1.85.46 2.69a2 2 0 0 1-.45 2.11z" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        </IconTile>
        <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">Your family checked, this was a scam.</h1>
        <p className="text-slate mb-6">Don't call back, don't send money.</p>
        <div className="w-full bg-danger-bg text-danger-ink rounded-2xl p-4 text-sm">
          You did the right thing checking.
        </div>
      </div>
      <Button variant="danger" onClick={() => navigate('/home')}>Stay safe and close</Button>
    </Screen>
  )
}
