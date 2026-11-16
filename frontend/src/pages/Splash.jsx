import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { homePathFor, useAuth } from '../AuthContext'
import Mascot from '../components/Mascot'

export default function Splash() {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const next = user ? homePathFor(user) : '/signin'

  useEffect(() => {
    if (loading) return undefined
    const timer = setTimeout(() => navigate(next), 4000)
    return () => clearTimeout(timer)
  }, [navigate, loading, next])

  return (
    <div className="min-h-screen flex items-start justify-center bg-[#eceeec] py-10 px-4">
      <div
        onClick={() => !loading && navigate(next)}
        className="w-full max-w-sm rounded-[28px] shadow-sm border border-black/5 min-h-[700px] flex flex-col items-center justify-center px-10 cursor-pointer"
        style={{ backgroundColor: '#f3ede1' }}
      >
        <Mascot mode="splash" className="-mt-6 mb-2" />
        <h1 className="fade-up text-3xl font-semibold text-ink mb-3" style={{ animationDelay: '1.2s' }}>CallBack</h1>
        <p className="fade-up text-center text-slate mb-14" style={{ animationDelay: '1.5s' }}>A calm second check before you act.</p>
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
