// Plays a pre-rendered mascot animation once. People who prefer reduced
// motion get the final still frame instead.
const SIZES = {
  splash: 'w-60 h-60',
  approved: 'w-44 h-48',
  denied: 'w-44 h-48',
}

export default function Mascot({ mode, className = '' }) {
  const still = !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  const file = still ? `mascot-${mode}-end.png` : `mascot-${mode}.webp`
  return (
    <img
      src={`/mascot/${file}`}
      alt=""
      aria-hidden="true"
      draggable="false"
      className={`pointer-events-none select-none ${SIZES[mode]} ${className}`}
    />
  )
}
