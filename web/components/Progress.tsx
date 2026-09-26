// Fills from the reading-direction start: right in Arabic, left in English.
export function Progress({ value, className = "" }: { value: number; className?: string }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className={`relative h-6 w-full overflow-hidden rounded-b-xl bg-[#eef0ef] ${className}`}>
      <div className="absolute inset-y-0 start-0 bg-brand-500 transition-[width] duration-700" style={{ width: `${v}%` }} />
      <span className="num absolute inset-y-0 flex items-center px-2 text-[12px] font-semibold text-white"
        style={{ insetInlineStart: `max(0px, calc(${v}% - 3.2rem))` }}>
        {Math.round(v)}%
      </span>
    </div>
  );
}
