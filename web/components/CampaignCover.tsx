// Generated cover art: category hue + an eight-point-star lattice + a glyph.
// Deterministic per campaign id, fully offline.

const GLYPHS: Record<string, string> = {
  family: "M32 26a6 6 0 1 0 0-12 6 6 0 0 0 0 12Zm-14 4a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm28 0a5 5 0 1 0 0-10 5 5 0 0 0 0 10ZM20 50V38a12 12 0 0 1 24 0v12M8 50v-8a9 9 0 0 1 12-8.5M56 50v-8a9 9 0 0 0-12-8.5",
  book: "M8 14h18a6 6 0 0 1 6 6v30a5 5 0 0 0-5-5H8zM56 14H38a6 6 0 0 0-6 6v30a5 5 0 0 1 5-5h19z",
  heart: "M32 52S8 38 8 22a12 12 0 0 1 24-3 12 12 0 0 1 24 3c0 16-24 30-24 30Zm-14-22h8l4-7 5 13 4-6h7",
  home: "M8 30 32 10l24 20M14 26v24h36V26M26 50V36h12v14",
  mosque: "M32 8v6M18 32a14 14 0 0 1 28 0H18Zm-6 0h40v20H12zM8 52V24M56 52V24M8 24l-2-4h4zM56 24l-2-4h4zM28 52V42a4 4 0 0 1 8 0v10",
  hands: "M10 34l10-10 8 4 8-4 10 2M6 44l10 6h18l20-12-4-4-14 6h-10M36 20l4-8 4 8-4 4z",
  wheel: "M28 10a4 4 0 1 0 0 .1M28 16v16h14l6 12M28 24h12M24 30a12 12 0 1 0 14 14",
  tree: "M32 56V34M32 34l-8-6M32 40l9-7M32 8c10 0 18 8 18 17a13 13 0 0 1-18 12 13 13 0 0 1-18-12C14 16 22 8 32 8Z",
  people: "M22 24a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm20 2a6 6 0 1 0 0-12 6 6 0 0 0 0 12ZM8 50a14 14 0 0 1 28 0M34 50a12 12 0 0 1 22-7",
  moon: "M40 10a22 22 0 1 0 14 34A18 18 0 0 1 40 10Zm8 4 1.5 3.5L53 19l-3.5 1.5L48 24l-1.5-3.5L43 19l3.5-1.5z",
  grid: "M10 10h18v18H10zM36 10h18v18H36zM10 36h18v18H10zM36 36h18v18H36z",
  pillar: "M8 14 32 6l24 8M10 14h44M14 20v26M24 20v26M40 20v26M50 20v26M8 52h48M10 46h44",
};

function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

export function CampaignCover({ id, hue, glyph, className = "", big = false }:
  { id: string; hue: number; glyph: string; className?: string; big?: boolean }) {
  const h = hash(id);
  const shift = (h % 24) - 12;
  const hh = (hue + shift + 360) % 360;
  const angle = h % 180;
  const pid = `p${h.toString(36)}`;
  const gid = `g${h.toString(36)}`;
  const d = GLYPHS[glyph] ?? GLYPHS.grid;
  return (
    <svg viewBox="0 0 400 220" preserveAspectRatio="xMidYMid slice" className={className} aria-hidden>
      <defs>
        <linearGradient id={gid} gradientTransform={`rotate(${angle} .5 .5)`}>
          <stop offset="0" stopColor={`hsl(${hh} 42% 86%)`} />
          <stop offset="1" stopColor={`hsl(${(hh + 18) % 360} 38% 68%)`} />
        </linearGradient>
        <pattern id={pid} width="44" height="44" patternUnits="userSpaceOnUse" patternTransform={`rotate(${h % 45})`}>
          <path d="M22 4 27 17 40 22 27 27 22 40 17 27 4 22 17 17Z" fill="none"
            stroke={`hsl(${hh} 35% 40%)`} strokeOpacity=".13" strokeWidth="1.2" />
        </pattern>
      </defs>
      <rect width="400" height="220" fill={`url(#${gid})`} />
      <rect width="400" height="220" fill={`url(#${pid})`} />
      <circle cx={80 + (h % 240)} cy={40 + (h % 60)} r={big ? 120 : 90} fill="#fff" opacity=".18" />
      <g transform={`translate(${big ? 168 : 168} 58) scale(${big ? 1.6 : 1.6})`}>
        <path d={d} fill="none" stroke={`hsl(${hh} 40% 26%)`} strokeOpacity=".72"
          strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  );
}
