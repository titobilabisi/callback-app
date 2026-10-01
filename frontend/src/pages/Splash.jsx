import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Splash() {
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => navigate('/home'), 1400)
    return () => clearTimeout(timer)
  }, [navigate])

  return (
    <div className="min-h-screen flex items-start justify-center bg-[#eceeec] py-10 px-4">
      <div
        onClick={() => navigate('/home')}
        className="w-full max-w-sm rounded-[28px] shadow-sm border border-black/5 min-h-[700px] flex flex-col items-center justify-center px-10 cursor-pointer"
        style={{ backgroundColor: '#f3ede1' }}
      >
        <div className="w-20 h-20 rounded-3xl bg-teal flex items-center justify-center text-white relative mb-6">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 4l5 1 1 4-2 2c1 3 3 5 6 6l2-2 4 1 1 5c-9 1-17-7-17-17z" />
          </svg>
          <span className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-white text-teal flex items-center justify-center text-sm">v</span>
        </div>
        <h1 className="text-3xl font-semibold text-ink mb-3">CallBack</h1>
        <p className="text-center text-slate mb-24">A calm second check before you act.</p>
        <div className="flex gap-2 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-teal" />
          <span className="w-1.5 h-1.5 rounded-full bg-teal/40" />
          <span className="w-1.5 h-1.5 rounded-full bg-teal/20" />
        </div>
        <p className="text-sm text-slate">Getting things ready</p>
      </div>
    </div>
  )
}
