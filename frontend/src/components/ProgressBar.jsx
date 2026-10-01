export default function ProgressBar({ step, total }) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-teal font-medium">A few quick questions</span>
        <span className="text-slate">{step} of {total}</span>
      </div>
      <div className="flex gap-1.5">
        {Array.from({ length: total }).map((_, i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full ${i < step ? 'bg-teal' : 'bg-teal-light'}`}
          />
        ))}
      </div>
    </div>
  )
}
