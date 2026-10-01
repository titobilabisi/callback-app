const tones = {
  teal: 'bg-teal-light text-teal',
  success: 'bg-success-bg text-success-ink',
  danger: 'bg-danger-bg text-danger-ink',
}

export default function IconTile({ tone = 'teal', children }) {
  return (
    <div className={`w-24 h-24 rounded-3xl flex items-center justify-center mx-auto ${tones[tone]}`}>
      {children}
    </div>
  )
}
