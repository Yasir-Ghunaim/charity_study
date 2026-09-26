"use client";

/** Yellow preview-only button, styled like the preview banner. */
export function SkipButton({ label, onClick, disabled }: { label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="rounded-xl border border-[#5c4300]/40 bg-[#fff4d6] px-5 py-2.5 text-[14px] font-semibold text-[#5c4300] hover:bg-[#ffecb3] disabled:opacity-60">
      {label}
    </button>
  );
}
