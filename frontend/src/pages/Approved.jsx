import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import StatusPill from '../components/StatusPill'
import IconTile from '../components/IconTile'
import Button from '../components/Button'

export default function Approved() {
  const navigate = useNavigate()

  return (
    <Screen>
      <AppHeader />
      <div className="flex-1 flex flex-col items-center text-center">
        <StatusPill tone="success">Checked and approved</StatusPill>
        <IconTile tone="success">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12l2 2 4-4" />
            <circle cx="12" cy="12" r="10" />
          </svg>
        </IconTile>
        <h1 className="text-2xl font-semibold text-ink mt-6 mb-6">Your family checked, this looks okay.</h1>
        <div className="w-full border border-black/10 rounded-2xl p-4 text-left">
          <p className="text-xs tracking-wide text-slate uppercase mb-1">Call details</p>
          <p className="text-ink">Insurance bill, $120.</p>
        </div>
      </div>
      <Button variant="success" onClick={() => navigate('/home')}>Call them back now</Button>
    </Screen>
  )
}
