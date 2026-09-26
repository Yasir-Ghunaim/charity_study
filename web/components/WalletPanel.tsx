"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { study } from "@/lib/client";
import { pick } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { useWallet } from "@/lib/wallet";

export function WalletPanel() {
  const w = useWallet();
  const { lang, t } = useLang();
  const router = useRouter();
  const [err, setErr] = useState("");
  if (!w) return null;
  const { wallet } = w;
  const pct = wallet.start ? (wallet.allocated / wallet.start) * 100 : 0;

  async function finish() {
    setErr("");
    if (!wallet.items.length) return setErr(t("finishNeedOne"));
    const q = wallet.remaining > 0 ? t("finishLeftover", { n: Math.round(wallet.remaining) }) : t("finishConfirm");
    if (!confirm(q)) return;
    try { await study.finish(); router.push("/survey/post"); router.refresh(); }
    catch (e) { setErr((e as Error).message); }
  }

  return (
    <aside className="rounded-2xl border border-line bg-white p-5 lg:sticky lg:top-24">
      <div className="text-[13px] text-muted">{t("walletLabel")}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="num text-[28px] font-bold text-brand-600">{Math.round(wallet.remaining).toLocaleString("en-US")}</span>
        <span className="text-[13px] text-muted">{t("left")} · {t("of")} <span className="num">{wallet.start.toLocaleString("en-US")}</span> {t("virtual")}</span>
      </div>
      <div className="mt-2 h-2 rounded bg-panel"><div className="h-2 rounded bg-brand-500 transition-[width]" style={{ width: `${pct}%` }} /></div>
      <div className="mt-5 text-[14px] font-semibold">{t("yourAllocations")}</div>
      {wallet.items.length === 0 ? (
        <p className="mt-2 text-[13px] text-muted">{t("noAllocations")}</p>
      ) : (
        <ul className="mt-2 divide-y divide-line">
          {wallet.items.map((i) => (
            <li key={i.campaign.id} className="flex items-center justify-between gap-3 py-2 text-[13.5px]">
              <Link href={`/campaigns/${i.campaign.id}`} className="truncate hover:text-brand-600">{pick(lang, i.campaign, "titleAr", "titleEn")}</Link>
              <span className="num shrink-0 font-semibold">{i.amount.toLocaleString("en-US")}</span>
            </li>
          ))}
        </ul>
      )}
      <button onClick={finish} className="mt-5 w-full rounded-xl bg-ink py-3 text-[14.5px] font-semibold text-white hover:bg-brand-900">{t("finish")}</button>
      {err && <div className="mt-2 text-[13px] text-ember-600">{err}</div>}
    </aside>
  );
}
