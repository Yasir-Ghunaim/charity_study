"use client";
import { useEffect, useRef, useState } from "react";
import { study } from "@/lib/client";
import { useLang } from "@/lib/lang";
import type { Campaign, Category } from "@/lib/types";
import { CampaignCard } from "./CampaignCard";
import { SearchIcon } from "./Icons";

const PAGE = 24;
type Sort = "relevance" | "popular" | "progress" | "newest";

/** Campaign explorer: search, category, filters, sort. Every query is logged for the study. */
export function BrowsePanel({ wallet }: { wallet: number }) {
  const { lang, t } = useLang();
  const [cats, setCats] = useState<Category[]>([]);
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [zakat, setZakat] = useState(false);
  const [nearly, setNearly] = useState(false);
  const [sort, setSort] = useState<Sort>("popular");
  const [items, setItems] = useState<Campaign[]>([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const first = useRef(true);

  useEffect(() => { fetch("/api/categories").then((r) => r.json()).then(setCats).catch(() => {}); }, []);

  async function load(offset: number) {
    setBusy(true);
    const qs = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
    if (q) qs.set("q", q);
    if (category) qs.set("category", category);
    if (zakat) qs.set("zakat", "true");
    if (nearly) qs.set("near_complete", "true");
    if (!q) qs.set("sort", sort === "relevance" ? "popular" : sort);   // text search is ordered by relevance
    try {
      const r = await (await fetch(`/api/campaigns?${qs}`)).json();
      setItems((prev) => (offset ? [...prev, ...r.items] : r.items));
      setTotal(r.total);
      if (!first.current) {
        study.log(offset ? "browse_load_more" : "browse_query", undefined,
          { q, category, zakat, nearly, sort: q ? "relevance" : sort, offset, results: r.total,
            shown: (r.items as Campaign[]).map((c) => c.id) });
      }
      first.current = false;
    } finally { setBusy(false); }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void load(0); }, [q, category, zakat, nearly, sort]);

  const chip = (on: boolean) =>
    `shrink-0 rounded-full border px-3.5 py-1.5 text-[13.5px] ${on ? "border-brand-500 bg-brand-500 text-white" : "border-line bg-white hover:border-brand-300"}`;

  return (
    <div className="rounded-3xl border border-line bg-white p-5 md:p-7">
      <h1 className="text-[24px] font-bold">{t("browseTitle")}</h1>
      <p className="mt-1 text-[14.5px] text-muted">{t("browseIntro", { wallet: wallet.toLocaleString("en-US") })}</p>

      <form onSubmit={(e) => { e.preventDefault(); setQ(text.trim()); if (text.trim()) setSort("relevance"); }}
        className="mt-5 flex gap-2">
        <div className="flex flex-1 items-center gap-2 rounded-xl border border-line px-3 focus-within:border-brand-500">
          <SearchIcon size={18} className="text-muted" />
          <input value={text} onChange={(e) => { setText(e.target.value); if (!e.target.value) setQ(""); }}
            placeholder={t("searchPlaceholder")} className="flex-1 bg-transparent py-2.5 text-[14.5px] outline-none" />
        </div>
        <button className="rounded-xl bg-brand-500 px-5 text-[14.5px] font-semibold text-white hover:bg-brand-600">{t("search")}</button>
      </form>

      <div className="no-scrollbar mt-4 flex gap-2 overflow-x-auto pb-1">
        <button onClick={() => setCategory("")} className={chip(!category)}>{t("all")}</button>
        {cats.map((c) => (
          <button key={c.id} onClick={() => setCategory(c.id === category ? "" : c.id)} className={chip(category === c.id)}>
            {lang === "en" ? c.nameEn : c.nameAr}
          </button>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-[13.5px]">
        <button onClick={() => setZakat((z) => !z)} className={chip(zakat)}>{t("onlyZakat")}</button>
        <button onClick={() => setNearly((n) => !n)} className={chip(nearly)}>{t("onlyNearly")}</button>
        {!q && (
          <label className="ms-auto flex items-center gap-2 text-muted">
            {t("sortBy")}
            <select value={sort} onChange={(e) => setSort(e.target.value as Sort)}
              className="rounded-lg border border-line bg-white px-2 py-1.5 text-ink outline-none">
              <option value="popular">{t("sortPopular")}</option>
              <option value="progress">{t("sortProgress")}</option>
              <option value="newest">{t("sortNewest")}</option>
            </select>
          </label>
        )}
        {q && <span className="ms-auto text-muted">{t("sortBy")}: {t("sortRelevance")}</span>}
      </div>

      <div className="mt-4 text-[13px] text-muted">{t("results", { n: total })}</div>
      {items.length === 0 && !busy ? (
        <div className="py-16 text-center text-muted">{t("noResults")}</div>
      ) : (
        <div className="mt-3 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((c) => <CampaignCard key={c.id} c={c} source="browse" />)}
        </div>
      )}
      {items.length < total && (
        <div className="mt-6 text-center">
          <button onClick={() => void load(items.length)} disabled={busy}
            className="rounded-xl border border-line px-6 py-2.5 text-[14px] hover:border-brand-500 disabled:opacity-50">{t("loadMore")}</button>
        </div>
      )}
    </div>
  );
}
