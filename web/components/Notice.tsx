export function Notice({ text }: { text: string }) {
  return <div className="rounded-3xl border border-line bg-white p-10 text-center text-[16px] leading-8 text-muted">{text}</div>;
}
