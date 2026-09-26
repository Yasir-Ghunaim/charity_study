"use client";
import Link from "next/link";
import { useState } from "react";
import { useLang } from "@/lib/lang";
import type { StudyPublic } from "@/lib/types";
import { Consent } from "./Consent";

/** A participant midway through another study opened this study's link. */
export function SwitchStudy({ study, continueHref }: { study: StudyPublic; continueHref: string }) {
  const { t } = useLang();
  const [join, setJoin] = useState(false);
  if (join) return <Consent study={study} />;
  return (
    <div className="rounded-3xl border border-line bg-white p-8 text-center">
      <h1 className="text-[22px] font-bold">{t("otherStudyTitle")}</h1>
      <p className="mx-auto mt-3 max-w-xl text-[15px] leading-7 text-muted">{t("otherStudyBody")}</p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link href={continueHref} className="rounded-xl bg-brand-500 px-6 py-3 text-[15px] font-semibold text-white hover:bg-brand-600">
          {t("continueCurrent")}
        </Link>
        <button onClick={() => setJoin(true)} className="rounded-xl border border-line px-6 py-3 text-[15px] hover:border-brand-500">
          {t("joinInstead")}
        </button>
      </div>
    </div>
  );
}
