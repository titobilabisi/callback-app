import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import IconTile from '../components/IconTile'
import Button from '../components/Button'
import { useCheck } from '../CheckContext'

export default function Home() {
  const navigate = useNavigate()
  const { reset } = useCheck()

  function startCheck() {
    reset()
    navigate('/check/1')
  }

  return (
    <Screen>
      <AppHeader />
      <div className="flex-1 flex flex-col items-center justify-center text-center">
        <IconTile tone="teal">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 16.92V21a1 1 0 0 1-1.1 1 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.7A1 1 0 0 1 4.3 3H8.4a1 1 0 0 1 1 .9c.1 1.1.3 2.2.7 3.3a1 1 0 0 1-.2 1L8.1 9.9a16 16 0 0 0 6 6l1.7-1.8a1 1 0 0 1 1-.2c1 .4 2.1.6 3.3.7a1 1 0 0 1 .9 1.1Z" />
          </svg>
        </IconTile>
        <h1 className="text-2xl font-semibold text-ink mt-6 mb-2">Let's check that call together</h1>
        <p className="text-slate">We'll help you check before you act.</p>
      </div>
      <div className="space-y-3">
        <Button variant="primary" onClick={startCheck}>I got a call, help me check</Button>
        <div className="flex items-center justify-center gap-2 text-sm text-teal bg-teal-light rounded-2xl py-3">
          <span>It's always okay to pause a call.</span>
        </div>
      </div>
    </Screen>
  )
}
