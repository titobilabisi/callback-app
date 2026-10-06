// Large, clearly labelled input. Labels sit above the field (not inside it)
// so they stay visible while typing.
export default function TextField({ label, id, ...props }) {
  return (
    <div className="mb-4">
      <label htmlFor={id} className="block text-sm font-medium text-ink mb-1.5">
        {label}
      </label>
      <input
        id={id}
        className="w-full rounded-2xl border-2 border-black/10 bg-white px-4 py-3.5 text-base text-ink focus:outline-none focus:border-teal"
        {...props}
      />
    </div>
  )
}
