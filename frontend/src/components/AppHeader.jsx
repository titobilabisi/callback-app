export default function AppHeader() {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div className="w-9 h-9 rounded-xl bg-teal flex items-center justify-center text-white relative">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 4l5 1 1 4-2 2c1 3 3 5 6 6l2-2 4 1 1 5c-9 1-17-7-17-17z" />
        </svg>
        <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-white text-teal flex items-center justify-center text-[10px]">v</span>
      </div>
      <span className="text-lg font-semibold text-ink">CallBack</span>
    </div>
  )
}
