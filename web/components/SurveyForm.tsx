"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { study } from "@/lib/client";
import { useLang } from "@/lib/lang";
import type { Survey } from "@/lib/types";

type Answer = string | number | (string | number)[];

export function SurveyForm({ survey, next, preview = false }: { survey: Survey; next: string; preview?: boolean }) {
  const { lang, t } = useLang();
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (id: string, v: Answer) => setAnswers((a) => ({ ...a, [id]: v }));

  async function skip() {
    setBusy(true); setErr("");
    try {
      const r = await fetch(`/api/study/survey/${survey.phase}/skip`, { method: "POST" });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? String(r.status));
      router.push(next); router.refresh();
    } catch (e) { setErr((e as Error).message); setBusy(false); }
  }

  async function submit() {
    const missing = survey.questions.filter((q) => q.required &&
      (answers[q.id] === undefined || answers[q.id] === "" || (Array.isArray(answers[q.id]) && !(answers[q.id] as []).length)));
    if (missing.length) {
      setErr(t("answerRequired"));
      document.getElementById(`q-${missing[0].id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    setBusy(true); setErr("");
    try { await study.survey(survey.phase, answers); router.push(next); router.refresh(); }
    catch (e) { setErr((e as Error).message); setBusy(false); }
  }

  return (
    <div className="space-y-4">
      {survey.questions.map((q, n) => (
        <fieldset key={q.id} id={`q-${q.id}`} className="rounded-2xl border border-line bg-white p-5">
          <legend className="sr-only">{q[lang]}</legend>
          <div className="text-[15.5px] font-semibold">
            <span className="num me-2 text-muted">{n + 1}.</span>{q[lang]}
            {q.required ? <span className="text-ember-500"> *</span> : <span className="ms-2 text-[12px] font-normal text-muted">({t("optional")})</span>}
          </div>
          {q.type === "text" && (
            <textarea rows={3} maxLength={2000} value={(answers[q.id] as string) ?? ""} onChange={(e) => set(q.id, e.target.value)}
              className="mt-3 w-full rounded-xl border border-line p-3 text-[14.5px] outline-none focus:border-brand-500" />
          )}
          {q.type === "likert" && (
            <div className="mt-3 grid grid-cols-5 gap-2">
              {q.options!.map((o) => (
                <button key={o.value} type="button" onClick={() => set(q.id, o.value)}
                  className={`rounded-xl border px-1 py-2.5 text-[12.5px] leading-5 ${answers[q.id] === o.value ? "border-brand-500 bg-brand-500 text-white" : "border-line hover:border-brand-300"}`}>
                  <div className="num text-[15px] font-bold">{o.value}</div>{o[lang]}
                </button>
              ))}
            </div>
          )}
          {(q.type === "single" || q.type === "multi") && (
            <div className="mt-3 flex flex-wrap gap-2">
              {q.options!.map((o) => {
                const cur = answers[q.id];
                const on = q.type === "multi" ? Array.isArray(cur) && cur.includes(o.value) : cur === o.value;
                return (
                  <button key={o.value} type="button"
                    onClick={() => {
                      if (q.type === "single") return set(q.id, o.value);
                      const arr = Array.isArray(cur) ? cur : [];
                      set(q.id, on ? arr.filter((x) => x !== o.value) : [...arr, o.value]);
                    }}
                    className={`rounded-full border px-4 py-2 text-[14px] ${on ? "border-brand-500 bg-brand-500 text-white" : "border-line hover:border-brand-300"}`}>
                    {o[lang]}
                  </button>
                );
              })}
            </div>
          )}
        </fieldset>
      ))}
      <div className="flex items-center gap-4">
        <button onClick={submit} disabled={busy}
          className="rounded-xl bg-brand-500 px-7 py-3 text-[15.5px] font-semibold text-white hover:bg-brand-600 disabled:opacity-60">
          {busy ? t("sending") : t("continue")}
        </button>
        {preview && (
          <button onClick={skip} disabled={busy}
            className="rounded-xl border border-[#5c4300]/40 bg-[#fff4d6] px-5 py-3 text-[14.5px] font-semibold text-[#5c4300] hover:bg-[#ffecb3] disabled:opacity-60">
            {t("skipSurvey")}
          </button>
        )}
        {err && <span className="text-[13.5px] text-ember-600">{err}</span>}
      </div>
    </div>
  );
}
