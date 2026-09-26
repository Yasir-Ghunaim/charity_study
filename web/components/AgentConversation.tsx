"use client";
import { useEffect, useRef, useState } from "react";
import { streamAgent } from "@/lib/client";
import { useLang } from "@/lib/lang";
import type { AgentEvent, UIBlock } from "@/lib/types";
import { Block } from "./AgentBlocks";
import { CheckIcon, SendIcon, SparkIcon } from "./Icons";

type Step = { labelAr: string; labelEn: string; tool: string; input: Record<string, unknown> };
type Turn = { question: string; steps: Step[]; blocks: UIBlock[]; texts: string[]; error?: string; done: boolean };

export function AgentConversation({ code, wallet }: { code: string; wallet: number }) {
  const { lang, t } = useLang();
  const key = `study_turns_${code}`;
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [limit, setLimit] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // keep the conversation when the participant opens a campaign page and comes back
  useEffect(() => {
    try { const s = sessionStorage.getItem(key); if (s) setTurns(JSON.parse(s)); } catch {}
    setLoaded(true);
  }, [key]);
  useEffect(() => {
    if (loaded) try { sessionStorage.setItem(key, JSON.stringify(turns.map((x) => ({ ...x, done: true })))); } catch {}
  }, [turns, loaded, key]);
  const lastLen = useRef(0);
  useEffect(() => {
    if (turns.length > lastLen.current) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    lastLen.current = turns.length;
  }, [turns]);

  const patch = (i: number, f: (x: Turn) => Turn) => setTurns((ts) => ts.map((x, j) => (j === i ? f(x) : x)));

  async function ask(q: string) {
    if (!q.trim() || busy || limit) return;
    const history = turns.flatMap((x) => [
      { role: "user", content: x.question },
      { role: "assistant", content: x.texts.join("\n") || "(cards shown)" },
    ]);
    const idx = turns.length;
    setTurns((ts) => [...ts, { question: q, steps: [], blocks: [], texts: [], done: false }]);
    setText(""); setBusy(true);
    try {
      await streamAgent(q, history, (e: AgentEvent) => {
        if (e.type === "step") patch(idx, (x) => ({ ...x, steps: [...x.steps, e] }));
        else if (e.type === "ui") patch(idx, (x) => ({ ...x, blocks: [...x.blocks, e.block] }));
        else if (e.type === "text") patch(idx, (x) => ({ ...x, texts: [...x.texts, e.text] }));
        else if (e.type === "error") patch(idx, (x) => ({ ...x, error: e.message }));
      });
    } catch (e) {
      if ((e as Error).message === "429") { setLimit(true); setTurns((ts) => ts.slice(0, -1)); }
      else patch(idx, (x) => ({ ...x, error: t("serverError") }));
    } finally {
      patch(idx, (x) => ({ ...x, done: true })); setBusy(false);
    }
  }

  return (
    <div className="rounded-3xl border border-line bg-white p-5 shadow-[0_8px_30px_rgba(23,50,34,.06)] md:p-7">
      {turns.length === 0 && (
        <div className="text-center">
          <h1 className="text-[26px] font-bold md:text-[30px]">{t("heading")}</h1>
          <p className="mx-auto mt-2 max-w-2xl text-[15px] leading-7 text-muted">{t("intro", { wallet: wallet.toLocaleString("en-US") })}</p>
        </div>
      )}
      <div className="space-y-8">
        {turns.map((x, i) => <TurnView key={i} t={x} last={i === turns.length - 1} />)}
        <div ref={endRef} />
      </div>
      {limit ? (
        <div className="mt-6 rounded-xl bg-panel p-4 text-[14px] text-muted">{t("limitReached")}</div>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); void ask(text); }}
          className={`flex items-center gap-2 rounded-2xl border border-line bg-panel p-2 focus-within:border-brand-500 ${turns.length ? "mt-8" : "mt-6"}`}>
          <input value={text} onChange={(e) => setText(e.target.value)} disabled={busy} maxLength={1000}
            placeholder={turns.length ? t("followPlaceholder") : t("askPlaceholder")}
            className="flex-1 bg-transparent px-3 py-3 text-[15px] outline-none" />
          <button disabled={busy || !text.trim()} className="flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-[15px] font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
            <SendIcon size={18} className={lang === "en" ? "-scale-x-100" : ""} /> {t("ask")}
          </button>
        </form>
      )}
      {turns.length === 0 && (
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {t("starters").split("|").map((s) => (
            <button key={s} onClick={() => void ask(s)}
              className="rounded-full border border-brand-200 bg-brand-50 px-3.5 py-1.5 text-[13px] text-brand-700 hover:bg-brand-100">{s}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function TurnView({ t: x, last }: { t: Turn; last: boolean }) {
  const { lang, t } = useLang();
  const [open, setOpen] = useState(false);
  const working = !x.done;
  const label = (s: Step) => (lang === "en" ? s.labelEn : s.labelAr);
  return (
    <div>
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl bg-brand-500 px-4 py-2.5 text-[15px] text-white">{x.question}</div>
      </div>
      <div className="mt-4 rounded-xl bg-panel px-4 py-3 text-[13px]">
        <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-2 text-start text-muted">
          <SparkIcon size={15} className={working ? "animate-spin text-brand-500 [animation-duration:2.5s]" : "text-brand-500"} />
          {working ? (x.steps.length ? label(x.steps[x.steps.length - 1]) : t("searching")) + "…" : t("stepsDone", { n: x.steps.length })}
          {x.steps.length > 0 && !working && <span className="ms-auto text-[12px] text-brand-600">{open ? t("hideSteps") : t("showSteps")}</span>}
        </button>
        {(open || (working && last)) && x.steps.length > 0 && (
          <ol className="mt-2 space-y-1.5">
            {x.steps.map((s, i) => (
              <li key={i} className="flex items-center gap-2">
                <CheckIcon size={14} className={i === x.steps.length - 1 && working ? "text-muted" : "text-brand-500"} />
                <span>{label(s)}</span>
              </li>
            ))}
          </ol>
        )}
      </div>
      {x.texts.length > 0 && (
        <div className="mt-4 whitespace-pre-wrap text-[15.5px] leading-8">{x.texts.join("\n\n").replace(/\*\*(.+?)\*\*/g, "«$1»")}</div>
      )}
      {x.blocks.length > 0 && <div className="mt-5 space-y-5">{x.blocks.map((b, i) => <Block key={i} b={b} />)}</div>}
      {x.error && <div className="mt-3 text-[12.5px] text-ember-600">{t("techNote")}: {x.error}</div>}
    </div>
  );
}
