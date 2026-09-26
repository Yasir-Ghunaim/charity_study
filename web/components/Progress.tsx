// Fills from the reading-direction start (right in Arabic, left in English).
// The label rides at the fill's leading edge; on short bars it sits just
// outside the fill in dark text so it stays readable.
export function Progress({ value, className = "" }: { value: number; className?: string }) {
  const v = Math.max(0, Math.min(100, Math.round(value)));
  const inside = v >= 18;
  return (
    <div className={`relative h-6 w-full overflow-hidden rounded-b-xl bg-[#eef0ef] ${className}`}>
      <div className="absolute inset-y-0 start-0 flex items-center justify-end bg-brand-500 transition-[width] duration-700"
        style={{ width: `${v}%` }}>
        {inside && <span className="num px-2 text-[12px] font-semibold text-white">{v}%</span>}
      </div>
      {!inside && (
        <span className="num absolute inset-y-0 flex items-center px-2 text-[12px] font-semibold text-ink"
          style={{ insetInlineStart: `${v}%` }}>{v}%</span>
      )}
    </div>
  );
}
