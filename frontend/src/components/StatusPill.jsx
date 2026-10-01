const tones = {
  teal: 'bg-teal-light text-teal',
  success: 'bg-success-bg text-success-ink',
  danger: 'bg-danger-bg text-danger-ink',
}

export default function StatusPill({ tone = 'teal', children }) {
  return (
    <span className={`inline-flex items-center gap-2 self-center px-4 py-1.5 rounded-full text-sm font-medium ${tones[tone]}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {children}
    </span>
  )
}
