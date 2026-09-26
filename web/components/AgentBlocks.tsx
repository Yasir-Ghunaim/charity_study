"use client";
import Link from "next/link";
import { useState } from "react";
import { pick } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import type { UIBlock } from "@/lib/types";
import { useWallet } from "@/lib/wallet";
import { CampaignCard } from "./CampaignCard";
import { CampaignCover } from "./CampaignCover";
import { CheckIcon } from "./Icons";
import { Amount } from "./Riyal";

const fmt = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 1 });

export function Block({ b }: { b: UIBlock }) {
  if (b.kind === "campaigns") return (
    <div className="rise">
      {b.heading && <div className="mb-3 text-[15px] font-semibold">{b.heading}</div>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {b.campaigns.map((c) => <CampaignCard key={c.id} c={c} source="agent_card" />)}
      </div>
    </div>
  );
  if (b.kind === "impact") return <ImpactCard b={b} />;
  if (b.kind === "comparison") return <Comparison b={b} />;
  return <Allocation b={b} />;
}

function ImpactCard({ b }: { b: Extract<UIBlock, { kind: "impact" }> }) {
  const { lang, t } = useLang();
  const { campaign: c, impact: i } = b;
  return (
    <div className="rise flex items-center gap-4 rounded-2xl border border-brand-200 bg-brand-50 p-4">
      <CampaignCover id={c.id} hue={c.hue} glyph={c.glyph} className="hidden h-16 w-24 shrink-0 rounded-lg sm:block" />
      <div className="flex-1 text-[14px] leading-7">
        <div>
          {t("impactWith", { a: `${fmt(i.amount_sar)} ${t("virtual")}` })}{" "}
          <Link href={`/campaigns/${c.id}`} className="font-semibold text-brand-600 hover:underline">{pick(lang, c, "titleAr", "titleEn")}</Link>
        </div>
        <div className="flex flex-wrap gap-x-5 text-muted">
          {i.units_funded !== null && <span>≈ <b className="num text-ink">{fmt(i.units_funded)}</b> × {i.unit}</span>}
          <span><b className="num text-ink">{fmt(i.share_of_remaining_pct)}%</b> {t("ofRemaining")}</span>
          {i.estimated_annual_yield_sar !== undefined && <span>{t("annualYield")} <b className="num text-ink">{fmt(i.estimated_annual_yield_sar)}</b></span>}
        </div>
      </div>
      {i.would_complete_campaign && <span className="shrink-0 rounded-full bg-ember-500 px-3 py-1 text-[12.5px] font-semibold text-white">{t("completes")}</span>}
    </div>
  );
}

function Comparison({ b }: { b: Extract<UIBlock, { kind: "comparison" }> }) {
  const { lang, t } = useLang();
  type R = (typeof b.rows)[number];
  const rows: [string, (r: R) => React.ReactNode][] = [
    [t("compareCharity"), (r) => r.charity],
    [t("compareRegion"), (r) => r.region],
    [t("compareProgress"), (r) => <span className="num">{r.progress_pct}%</span>],
    [t("compareRemaining"), (r) => <Amount value={r.remaining_sar} />],
    [t("compareUnit"), (r) => r.unit ? <>{r.unit} · <Amount value={r.unit_cost_sar ?? 0} /></> : "—"],
    [t("compareZakat"), (r) => (r.zakat_eligible ? t("yes") : t("no"))],
    [t("compareWaqf"), (r) => (r.waqf ? t("yes") : t("no"))],
    [t("compareGov"), (r) => r.charity_governance_score !== null ? <span className="num">{r.charity_governance_score}/100</span> : "—"],
    [t("compareOverhead"), (r) => r.charity_overhead_pct !== null ? <span className="num">{r.charity_overhead_pct}%</span> : "—"],
    [t("compareAudit"), (r) => r.charity_audited_year ?? t("notPublished")],
  ];
  return (
    <div className="rise space-y-6">
      <div className="overflow-x-auto rounded-2xl border border-line">
        <table className="w-full min-w-[560px] text-[13.5px]">
          <thead><tr className="bg-panel">
            <th className="w-40 px-3 py-3" />
            {b.rows.map((r) => (
              <th key={r.campaign_id} className="px-3 py-3 text-start font-semibold">
                <Link href={`/campaigns/${r.campaign_id}`} className="text-brand-600 hover:underline">{r.title}</Link>
              </th>
            ))}
          </tr></thead>
          <tbody>
            {rows.map(([label, get]) => (
              <tr key={label} className="border-t border-line">
                <td className="px-3 py-2.5 text-muted">{label}</td>
                {b.rows.map((r) => <td key={r.campaign_id} className="px-3 py-2.5">{get(r)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div>
        <div className="mb-3 text-[15px] font-semibold">{t("allocateEither")}</div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {b.campaigns.map((c) => <CampaignCard key={c.id} c={c} source="agent_compare" />)}
        </div>
      </div>
      {b.alternatives?.map((g) => (
        <div key={g.categoryId}>
          <div className="mb-3 text-[15px] font-semibold">{t("moreIn", { c: lang === "en" ? g.categoryEn : g.categoryAr })}</div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {g.campaigns.map((c) => <CampaignCard key={c.id} c={c} source="agent_alternative" />)}
          </div>
        </div>
      ))}
    </div>
  );
}

function Allocation({ b }: { b: Extract<UIBlock, { kind: "allocation" }> }) {
  const { lang, t } = useLang();
  const w = useWallet();
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [err, setErr] = useState("");
  async function accept() {
    if (!w) return;
    setState("busy"); setErr("");
    try {
      await w.allocateBatch(b.items.map((i) => ({ campaignId: i.campaign.id, amount: i.amount })), "agent_proposal");
      setState("done");
    } catch (e) { setErr((e as Error).message); setState("idle"); }
  }
  return (
    <div className="rise rounded-2xl border-2 border-brand-300 bg-white p-5">
      <div className="text-[16px] font-bold">{t("suggestedSplit")}</div>
      {b.note && <p className="mt-1 text-[13.5px] text-muted">{b.note}</p>}
      <div className="mt-3 divide-y divide-line">
        {b.items.map((it) => (
          <div key={it.campaign.id} className="flex items-center gap-3 py-2.5">
            <CampaignCover id={it.campaign.id} hue={it.campaign.hue} glyph={it.campaign.glyph} className="h-11 w-16 shrink-0 rounded-md" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-[14px] font-semibold">{pick(lang, it.campaign, "titleAr", "titleEn")}</div>
              {it.units !== null && <div className="text-[12px] text-muted">≈ <span className="num">{fmt(it.units)}</span> × {pick(lang, it.campaign, "unitAr", "unitEn")}</div>}
            </div>
            <span className="num font-semibold">{fmt(it.amount)}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-line pt-3">
        <div className="text-[15px]">{t("total")} <b className="num">{fmt(b.total)}</b> {t("virtual")}</div>
        {state === "done" ? (
          <span className="flex items-center gap-1.5 rounded-lg bg-brand-50 px-4 py-2 text-[14px] font-semibold text-brand-700"><CheckIcon size={16} /> {t("splitDone")}</span>
        ) : w?.enabled ? (
          <button onClick={accept} disabled={state === "busy"}
            className="rounded-lg bg-brand-500 px-4 py-2 text-[14px] font-semibold text-white hover:bg-brand-600 disabled:opacity-60">{t("acceptSplit")}</button>
        ) : null}
      </div>
      {err && <div className="mt-2 text-[13px] text-ember-600">{err}</div>}
    </div>
  );
}
