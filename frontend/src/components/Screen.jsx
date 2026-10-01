// Shared page shell. Keeps every screen the same width and spacing so the
// app reads as one connected flow instead of separate pages.
export default function Screen({ children }) {
  return (
    <div className="min-h-screen flex items-start justify-center bg-[#eceeec] py-10 px-4">
      <div className="w-full max-w-sm bg-white rounded-[28px] shadow-sm border border-black/5 min-h-[700px] flex flex-col p-6">
        {children}
      </div>
    </div>
  )
}
