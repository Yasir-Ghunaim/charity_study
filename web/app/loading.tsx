// Shown the instant a participant navigates, while the next page is prepared.
export default function Loading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <span className="spinner text-[28px] text-brand-500" />
    </div>
  );
}
