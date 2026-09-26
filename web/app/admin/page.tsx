"use client";
import { useCallback, useEffect, useState } from "react";

type Mode = "assistant" | "assistant_browse" | "browse";
type Study = {
  id: string; name: string; mode: Mode; wallet: number; maxTurns: number; preSurvey: boolean; postSurvey: boolean;
  status: "draft" | "open" | "closed"; notes: string; createdAt: string; participants: Record<string, number>;
  locked: boolean; consentVersion: string;
};
type Engines = { openai: boolean; anthropic: boolean; ollama: boolean; models: Record<string, string> };
type Summary = {
  storage: string; participants: Record<string, number>; agentTurns: number; events: number; allocated: number;
  engines: Record<string, number>; topCampaigns: { title_en: string; n: number; total: number }[];
};

const MODES: Record<Mode, { label: string; hint: string }> = {
  assistant: { label: "Assistant only", hint: "Participants find and compare campaigns by talking to the AI assistant." },
  assistant_browse: { label: "Assistant + browse", hint: "Two tabs: the AI assistant, and a campaign explorer with search and filters." },
  browse: { label: "Browse only", hint: "Campaign explorer only, no AI. Useful as a control group." },
};
const EXPORTS = ["participants", "surveys", "allocations", "events", "agent_turns", "studies", "campaigns"];
const blank = (): Partial<Study> => ({ id: "", name: "", mode: "assistant", wallet: 1000, maxTurns: 25, preSurvey: true, postSurvey: true, status: "draft", notes: "" });

export default function Admin() {
  const [token, setToken] = useState("");
  const [authed, setAuthed] = useState(false);
  const [studies, setStudies] = useState<Study[]>([]);
  const [engines, setEngines] = useState<Engines | null>(null);
  const [editing, setEditing] = useState<Partial<Study> | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [filter, setFilter] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [msg, setMsg] = useState("");
  const [copied, setCopied] = useState("");

  const call = useCallback(async (path: string, init: RequestInit = {}) => {
    const r = await fetch(`/api/study/admin${path}`, {
      ...init, headers: { "content-type": "application/json", "x-admin-token": token, ...(init.headers || {}) },
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? r.status));
    return body;
  }, [token]);

  const refresh = useCallback(async () => {
    const d = await call("/studies");
    setStudies(d.studies); setEngines(d.engines);
    setSummary(await call(`/summary${filter ? `?study=${encodeURIComponent(filter)}` : ""}`));
  }, [call, filter]);

  useEffect(() => { try { const t = sessionStorage.getItem("admin_token"); if (t) setToken(t); } catch {} }, []);
  useEffect(() => { if (authed) refresh().catch((e) => setMsg(e.message)); }, [authed, filter, refresh]);

  async function login() {
    setMsg("");
    try { await call("/studies"); setAuthed(true); try { sessionStorage.setItem("admin_token", token); } catch {} }
    catch { setMsg("Wrong token, or STUDY_ADMIN_TOKEN is not set on the API."); }
  }

  async function save() {
    if (!editing) return;
    setMsg("");
    const body = { ...editing, id: isNew ? (editing.id || undefined) : undefined };
    try {
      if (isNew) await call("/studies", { method: "POST", body: JSON.stringify(body) });
      else await call(`/studies/${editing.id}`, { method: "PATCH", body: JSON.stringify(body) });
      setEditing(null); await refresh();
    } catch (e) { setMsg((e as Error).message); }
  }

  async function setStatus(s: Study, status: Study["status"]) {
    setMsg("");
    try { await call(`/studies/${s.id}`, { method: "PATCH", body: JSON.stringify({ status }) }); await refresh(); }
    catch (e) { setMsg((e as Error).message); }
  }

  async function remove(s: Study) {
    if (!confirm(`Delete study "${s.name}"? This only works while it has no participants.`)) return;
    try { await call(`/studies/${s.id}`, { method: "DELETE" }); await refresh(); } catch (e) { setMsg((e as Error).message); }
  }

  const link = (id: string) => `${typeof window !== "undefined" ? window.location.origin : ""}/s/${id}`;
  const copy = async (id: string) => { await navigator.clipboard.writeText(link(id)); setCopied(id); setTimeout(() => setCopied(""), 1500); };
  const n = (s: Study) => Object.values(s.participants).reduce((a, b) => a + b, 0);
  const engineLine = engines && (engines.openai ? `ChatGPT (${engines.models.openai})`
    : engines.anthropic ? `Claude (${engines.models.anthropic})`
    : engines.ollama ? `local model (${engines.models.ollama})` : "rule-based fallback only: add OPENAI_API_KEY and OPENAI_MODEL");
  const input = "w-full rounded-lg border border-line bg-white px-3 py-2 outline-none focus:border-brand-500 disabled:bg-panel disabled:text-muted";

  if (!authed) return (
    <main dir="ltr" className="mx-auto max-w-md px-5 py-16">
      <h1 className="text-2xl font-bold">Study admin</h1>
      <form onSubmit={(e) => { e.preventDefault(); void login(); }} className="mt-5 flex gap-2">
        <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="STUDY_ADMIN_TOKEN" className={input} />
        <button className="rounded-lg bg-brand-500 px-4 font-semibold text-white">Sign in</button>
      </form>
      {msg && <p className="mt-3 text-ember-600">{msg}</p>}
    </main>
  );

  return (
    <main dir="ltr" className="mx-auto max-w-6xl px-5 py-10 text-[14px]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Study admin</h1>
        <div className="text-muted">AI studies use: <b className="text-ink">{engineLine}</b> · data in {summary?.storage}</div>
      </div>
      {msg && <div className="mt-4 rounded-lg bg-[#fff4ef] px-4 py-2.5 text-ember-600">{msg}</div>}

      {/* ------------------------------------------------------------ studies */}
      <section className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Studies</h2>
          <button onClick={() => { setIsNew(true); setEditing(blank()); setMsg(""); }}
            className="rounded-lg bg-brand-500 px-4 py-2 font-semibold text-white">New study</button>
        </div>
        <div className="mt-3 overflow-x-auto rounded-xl border border-line bg-white">
          <table className="w-full min-w-[860px]">
            <thead className="bg-panel text-left text-[12.5px] text-muted">
              <tr>{["Study", "Interface", "Wallet", "AI msgs", "Surveys", "Participants", "Status", "Link", ""].map((h) => <th key={h} className="px-3 py-2.5 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {studies.length === 0 && <tr><td colSpan={9} className="px-3 py-6 text-center text-muted">No studies yet. Create one to get a participant link.</td></tr>}
              {studies.map((s) => (
                <tr key={s.id} className="border-t border-line align-top">
                  <td className="px-3 py-3"><div className="font-semibold">{s.name}</div><div className="font-mono text-[12px] text-muted">{s.id}</div></td>
                  <td className="px-3 py-3">{MODES[s.mode].label}</td>
                  <td className="px-3 py-3">{s.wallet.toLocaleString()}</td>
                  <td className="px-3 py-3">{s.mode === "browse" ? "—" : s.maxTurns}</td>
                  <td className="px-3 py-3">{[s.preSurvey && "pre", s.postSurvey && "post"].filter(Boolean).join(" + ") || "none"}</td>
                  <td className="px-3 py-3">{n(s)}{n(s) > 0 && <div className="text-[12px] text-muted">{Object.entries(s.participants).map(([k, v]) => `${k} ${v}`).join(" · ")}</div>}</td>
                  <td className="px-3 py-3">
                    <select value={s.status} onChange={(e) => setStatus(s, e.target.value as Study["status"])}
                      className={`rounded-md border px-2 py-1 ${s.status === "open" ? "border-brand-500 text-brand-700" : "border-line"}`}>
                      <option value="draft">draft</option><option value="open">open</option><option value="closed">closed</option>
                    </select>
                  </td>
                  <td className="px-3 py-3"><button onClick={() => copy(s.id)} className="text-brand-600 hover:underline">{copied === s.id ? "copied ✓" : "copy link"}</button></td>
                  <td className="px-3 py-3 text-right">
                    <button onClick={() => { setIsNew(false); setEditing({ ...s }); setMsg(""); }} className="text-brand-600 hover:underline">edit</button>
                    {n(s) === 0 && <button onClick={() => remove(s)} className="ms-3 text-muted hover:text-ember-600">delete</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[12.5px] text-muted">Only <b>open</b> studies accept participants. Once a study has participants its design is locked; to change it, create a new study.</p>
      </section>

      {/* ----------------------------------------------------------- editor */}
      {editing && (
        <section className="mt-6 rounded-xl border-2 border-brand-300 bg-white p-5">
          <h2 className="text-lg font-semibold">{isNew ? "New study" : `Edit “${editing.name}”`}</h2>
          {editing.locked && <p className="mt-1 text-ember-600">This study has participants: only name, notes and status can change.</p>}
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="block">Name (for you only)
              <input className={`${input} mt-1`} value={editing.name ?? ""} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /></label>
            <label className="block">Study ID (used in the link: /s/&lt;id&gt;)
              <input className={`${input} mt-1 font-mono`} disabled={!isNew} placeholder="auto if left empty, e.g. ramadan-pilot"
                value={editing.id ?? ""} onChange={(e) => setEditing({ ...editing, id: e.target.value.toLowerCase() })} /></label>
          </div>
          <fieldset className="mt-4" disabled={editing.locked}>
            <legend>Interface</legend>
            <div className="mt-1 grid gap-2 md:grid-cols-3">
              {(Object.keys(MODES) as Mode[]).map((m) => (
                <label key={m} className={`cursor-pointer rounded-lg border p-3 ${editing.mode === m ? "border-brand-500 bg-brand-50" : "border-line"} ${editing.locked ? "opacity-60" : ""}`}>
                  <input type="radio" className="me-2 accent-brand-500" checked={editing.mode === m} onChange={() => setEditing({ ...editing, mode: m })} />
                  <b>{MODES[m].label}</b><div className="mt-1 text-[12.5px] text-muted">{MODES[m].hint}</div>
                </label>
              ))}
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-4">
              <label className="block">Virtual wallet
                <input type="number" min={10} className={`${input} mt-1`} value={editing.wallet ?? 1000} onChange={(e) => setEditing({ ...editing, wallet: Number(e.target.value) })} /></label>
              <label className="block">AI message limit
                <input type="number" min={1} max={200} disabled={editing.mode === "browse" || editing.locked} className={`${input} mt-1`}
                  value={editing.maxTurns ?? 25} onChange={(e) => setEditing({ ...editing, maxTurns: Number(e.target.value) })} /></label>
              <label className="mt-6 flex items-center gap-2"><input type="checkbox" className="accent-brand-500" checked={!!editing.preSurvey} onChange={(e) => setEditing({ ...editing, preSurvey: e.target.checked })} /> Pre-survey</label>
              <label className="mt-6 flex items-center gap-2"><input type="checkbox" className="accent-brand-500" checked={!!editing.postSurvey} onChange={(e) => setEditing({ ...editing, postSurvey: e.target.checked })} /> Post-survey</label>
            </div>
          </fieldset>
          <label className="mt-4 block">Notes (for you only)
            <textarea rows={2} className={`${input} mt-1`} value={editing.notes ?? ""} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} /></label>
          <div className="mt-4 flex gap-2">
            <button onClick={save} className="rounded-lg bg-brand-500 px-5 py-2 font-semibold text-white">{isNew ? "Create (as draft)" : "Save"}</button>
            <button onClick={() => setEditing(null)} className="rounded-lg border border-line px-5 py-2">Cancel</button>
          </div>
        </section>
      )}

      {/* -------------------------------------------------------------- data */}
      <section className="mt-10">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold">Data</h2>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="rounded-lg border border-line bg-white px-3 py-1.5">
            <option value="">All studies</option>
            {studies.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.id})</option>)}
          </select>
        </div>
        {summary && (
          <div className="mt-3 grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-line bg-white p-4">
              <div className="text-muted">Participants</div>
              <div className="mt-1 text-2xl font-bold">{Object.values(summary.participants).reduce((a, b) => a + b, 0)}</div>
              <div className="text-[12.5px] text-muted">{Object.entries(summary.participants).map(([k, v]) => `${k} ${v}`).join(" · ") || "none yet"}</div>
            </div>
            <div className="rounded-xl border border-line bg-white p-4">
              <div className="text-muted">Activity</div>
              <div className="mt-1">{summary.agentTurns} AI messages · {summary.events} events</div>
              <div>{Math.round(summary.allocated).toLocaleString()} virtual SAR allocated</div>
              <div className="text-[12.5px] text-muted">{Object.entries(summary.engines).map(([k, v]) => `${k}: ${v}`).join(", ")}</div>
            </div>
            <div className="rounded-xl border border-line bg-white p-4">
              <div className="text-muted">Top campaigns</div>
              <ol className="mt-1 list-decimal ps-5 text-[13px]">{summary.topCampaigns.slice(0, 5).map((c) => <li key={c.title_en}>{c.title_en}: {Math.round(c.total)}</li>)}</ol>
            </div>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          {EXPORTS.map((x) => (
            <a key={x} className="rounded-lg border border-line bg-white px-3 py-1.5 hover:border-brand-500"
              href={`/api/study/admin/export/${x}.csv?token=${encodeURIComponent(token)}${filter && !["studies", "campaigns"].includes(x) ? `&study=${encodeURIComponent(filter)}` : ""}`}>
              {x}{filter && !["studies", "campaigns"].includes(x) ? ` (${filter})` : ""}.csv
            </a>
          ))}
        </div>
        <p className="mt-2 text-[12.5px] text-muted">CSV links carry your token; don&apos;t share them. Every row includes study_id.</p>
      </section>
    </main>
  );
}
