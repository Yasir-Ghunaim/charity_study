// Saudi riyal sign drawn as SVG: U+20C1 is too new for most system fonts.
export function Riyal({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-label="ريال" role="img"
      className={`inline-block h-[0.95em] w-[0.95em] align-[-0.1em] ${className}`}
      fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13.2 2.8v14.4" />
      <path d="M8.4 5.2v10.6c0 1.8-1 2.8-2.6 3.4" />
      <path d="M3.6 11.8 20.4 8.2" />
      <path d="M3.6 16 20.4 12.4" />
      <path d="M14.6 20.6 20.4 19.4" />
    </svg>
  );
}

export function Amount({ value, className = "" }: { value: number; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 ${className}`}>
      <Riyal />
      <span className="num">{new Intl.NumberFormat("en-US").format(Math.round(value))}</span>
    </span>
  );
}
