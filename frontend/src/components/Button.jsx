const base =
  'w-full rounded-2xl py-4 text-base font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2'

const variants = {
  primary: `${base} bg-teal text-white hover:bg-teal-dark`,
  success: `${base} bg-success text-white hover:brightness-95`,
  danger: `${base} bg-danger text-white hover:brightness-95`,
  // Used for Yes/No and Approve/Decline. Both options in a pair use this
  // same style so neither answer looks like the "correct" or default one.
  choice: `${base} border-2 border-teal text-teal bg-white hover:bg-teal-light`,
  ghost: `${base} bg-teal-light text-teal`,
}

export default function Button({ variant = 'primary', children, ...props }) {
  return (
    <button className={variants[variant] || variants.primary} {...props}>
      {children}
    </button>
  )
}
