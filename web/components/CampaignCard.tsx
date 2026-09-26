"use client";
import Link from "next/link";
import { study } from "@/lib/client";
import { pick } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import type { Campaign } from "@/lib/types";
import { AllocationControl } from "./AllocationControl";
import { CampaignCover } from "./CampaignCover";
import { StarIcon } from "./Icons";
import { Progress } from "./Progress";
import { Amount } from "./Riyal";

export function CampaignCard({ c, source = "card" }: { c: Campaign; source?: string }) {
  const { lang, t } = useLang();
  const open = () => study.log("open_details", c.id, { from: source });
  return (
    <article className="flex h-full flex-col rounded-2xl border border-line bg-white p-4">
      <Link href={`/campaigns/${c.id}`} onClick={open} className="relative block overflow-hidden rounded-xl">
        <CampaignCover id={c.id} hue={c.hue} glyph={c.glyph} className="aspect-[400/190] w-full" />
        {c.nearComplete && (
          <span className="absolute bottom-9 end-3 flex items-center gap-1.5 rounded-md bg-ember-500 px-2.5 py-1 text-[12.5px] font-semibold text-white shadow">
            <StarIcon size={14} /> {t("almostFunded")}
          </span>
        )}
        {c.isZakat && (
          <span className="absolute start-3 top-3 rounded-full bg-white/90 px-2.5 py-0.5 text-[11.5px] font-semibold text-brand-700">{t("zakat")}</span>
        )}
        <Progress value={c.progressPct} />
      </Link>
      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="rounded-md border border-line px-2 py-0.5 text-[12px]">{pick(lang, c, "categoryNameAr", "categoryNameEn")}</span>
        <span className="truncate text-[12px] text-muted">{pick(lang, c, "region", "regionEn")}</span>
      </div>
      <Link href={`/campaigns/${c.id}`} onClick={open} className="mt-2 text-[16px] font-bold leading-7 text-brand-600 hover:text-brand-700">
        {pick(lang, c, "titleAr", "titleEn")}
      </Link>
      <div className="text-[12.5px] text-muted">{pick(lang, c, "charity", "charityEn")}</div>
      <div className="mt-3 grid grid-cols-2 gap-2 rounded-xl bg-panel px-3 py-2.5">
        <div><div className="text-[12.5px] text-brand-600">{t("raised")}</div><Amount value={c.raisedAmount} className="text-[14.5px] font-bold" /></div>
        <div><div className="text-[12.5px] text-brand-600">{t("remaining")}</div><Amount value={c.remainingAmount} className="text-[14.5px] font-bold" /></div>
      </div>
      <div className="mt-3"><AllocationControl c={c} source={source} /></div>
      <div className="mt-auto pt-3 text-center">
        <Link href={`/campaigns/${c.id}`} onClick={open} className="text-[13.5px] text-muted hover:text-brand-600">{t("details")}</Link>
      </div>
    </article>
  );
}
