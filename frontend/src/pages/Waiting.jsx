import { useNavigate } from 'react-router-dom'
import Screen from '../components/Screen'
import AppHeader from '../components/AppHeader'
import IconTile from '../components/IconTile'

export default function Waiting() {
  const navigate = useNavigate()

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
        <p className="text-slate">We're checking with your family.</p>
      </div>

      <div className="bg-teal-light text-teal rounded-2xl py-3 text-center text-sm mb-3">
        Stay on this screen
      </div>

      {/* Demo controls: this prototype does not yet have a live verifier
          connection (that is Chunk 3 of the build). These links stand in
          for a family member responding on their own phone. */}
      <div className="border-t border-black/5 pt-3 text-center">
        <p className="text-xs text-slate mb-2">Demo only, not part of the real app</p>
        <div className="flex gap-2 text-xs">
          <button onClick={() => navigate('/result/approved')} className="flex-1 py-2 rounded-xl bg-success-bg text-success-ink">Simulate approved</button>
          <button onClick={() => navigate('/result/denied')} className="flex-1 py-2 rounded-xl bg-danger-bg text-danger-ink">Simulate denied</button>
          <button onClick={() => navigate('/result/timeout')} className="flex-1 py-2 rounded-xl bg-teal-light text-teal">Simulate timeout</button>
        </div>
      </div>
    </Screen>
  )
}
