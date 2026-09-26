"use client";
import { useState } from "react";
import { useLang } from "@/lib/lang";
import type { Campaign } from "@/lib/types";
import { useWallet } from "@/lib/wallet";
import { CheckIcon, TrashIcon } from "./Icons";

/** Allocate virtual riyals to one campaign (used on cards and the detail page). */
export function AllocationControl({ c, source, big = false }: { c: Campaign; source: string; big?: boolean }) {
  const w = useWallet();
  const { t } = useLang();
  const current = w?.amountFor(c.id) ?? 0;
  const [value, setValue] = useState(current ? String(current) : "");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  if (!w) return null;
  const remainingForThis = w.wallet.remaining + current;

  async function save(amount: number) {
    if (!w) return;
    if (amount > 0 && amount < c.minDonation) return setMsg({ ok: false, text: t("minAmount", { n: c.minDonation }) });
    if (amount > remainingForThis) return setMsg({ ok: false, text: t("notEnough", { n: Math.round(remainingForThis) }) });
    setBusy(true);
    try {
      await w.allocate(c.id, amount, source);
      setMsg({ ok: true, text: t("saved") });
      if (!amount) setValue("");
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally { setBusy(false); }
  }

  const quick = [50, 100, 250].filter((q) => q >= c.minDonation && q <= remainingForThis);
  return (
    <div>
      {current > 0 && (
        <div className="mb-2 flex items-center justify-between rounded-lg bg-brand-50 px-3 py-1.5 text-[13px] text-brand-700">
          <span className="flex items-center gap-1.5"><CheckIcon size={14} /> {t("allocatedHere")}: <b className="num">{current}</b></span>
          <button disabled={!w.enabled || busy} onClick={() => save(0)} className="flex items-center gap-1 hover:text-ember-600">
            <TrashIcon size={14} /> {t("remove")}
          </button>
        </div>
      )}
      {w.enabled && (
        <>
          {quick.length > 0 && (
            <div className="mb-2 flex gap-1.5">
              {quick.map((q) => (
                <button key={q} onClick={() => setValue(String(q))}
                  className={`num flex-1 rounded-md border py-1 text-[12.5px] ${value === String(q) ? "border-brand-500 bg-brand-50 text-brand-700" : "border-line hover:border-brand-300"}`}>
                  {q}
                </button>
              ))}
            </div>
          )}
          <div className="flex items-stretch gap-2">
            <input inputMode="numeric" placeholder={t("amount")} value={value}
              onChange={(e) => { setValue(e.target.value.replace(/[^\d]/g, "")); setMsg(null); }}
              className={`num min-w-0 flex-1 rounded-lg border border-line px-3 text-[14px] outline-none focus:border-brand-500 ${big ? "py-3" : "py-2.5"}`} />
            <button disabled={busy || !value} onClick={() => save(Number(value))}
              className="shrink-0 rounded-lg bg-brand-500 px-4 text-[14px] font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
              {current ? t("update") : t("allocate")}
            </button>
          </div>
        </>
      )}
      {msg && <div className={`mt-1.5 text-[12.5px] ${msg.ok ? "text-brand-600" : "text-ember-600"}`}>{msg.text}</div>}
    </div>
  );
}
