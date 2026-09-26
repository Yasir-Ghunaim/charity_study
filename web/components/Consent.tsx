"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { study as api } from "@/lib/client";
import { useLang } from "@/lib/lang";
import type { StudyPublic } from "@/lib/types";

export function Consent({ study }: { study: StudyPublic }) {
  const { lang, t } = useLang();
  const router = useRouter();
  const c = study.consent[lang];
  const [checks, setChecks] = useState([false, false]);
  const [nick, setNick] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function start() {
    setErr("");
    if (!checks.every(Boolean)) return setErr(t("consentNeeded"));
    if (nick.trim().length < 2) return setErr(t("nicknameNeeded"));
    setBusy(true);
    try {
      await api.join({ studyId: study.id, nickname: nick.trim(), lang, adult: checks[0], consent: checks[1],
        consentVersion: study.consent.version });
      router.push(study.preSurvey ? "/survey/pre" : "/study"); router.refresh();
    } catch (e) { setErr((e as Error).message); setBusy(false); }
  }

  return (
    <div className="rounded-3xl border border-line bg-white p-6 md:p-8">
      <h1 className="text-[24px] font-bold md:text-[28px]">{c.title}</h1>
      <div className="mt-5 space-y-4">
        {c.sections.map((s) => (
          <section key={s.heading}>
            <h2 className="text-[15.5px] font-semibold text-brand-700">{s.heading}</h2>
            <p className="mt-1 text-[14.5px] leading-7 text-ink/85">{s.body}</p>
          </section>
        ))}
      </div>
      <div className="mt-6 space-y-2.5 rounded-2xl bg-panel p-4">
        {c.checks.map((label, i) => (
          <label key={i} className="flex cursor-pointer items-start gap-3 text-[14.5px]">
            <input type="checkbox" checked={checks[i]} className="mt-1 h-4 w-4 accent-brand-500"
              onChange={(e) => setChecks((cs) => cs.map((v, j) => (j === i ? e.target.checked : v)))} />
            {label}
          </label>
        ))}
      </div>
      <div className="mt-5">
        <label className="text-[14.5px] font-semibold" htmlFor="nick">{t("nicknameLabel")}</label>
        <input id="nick" value={nick} maxLength={24} onChange={(e) => setNick(e.target.value)}
          className="mt-1.5 w-full rounded-xl border border-line px-4 py-3 text-[15px] outline-none focus:border-brand-500 md:w-80" />
        <p className="mt-1 text-[12.5px] text-muted">{t("nicknameHint")}</p>
      </div>
      <button onClick={start} disabled={busy}
        className="mt-6 rounded-xl bg-brand-500 px-7 py-3 text-[15.5px] font-semibold text-white hover:bg-brand-600 disabled:opacity-60">{t("start")}</button>
      {err && <div className="mt-3 text-[13.5px] text-ember-600">{err}</div>}
    </div>
  );
}
