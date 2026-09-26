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
  const [busy, setBusy] = useState<string | null>(null);      // which action is in flight
  const [toast, setToast] = useState("");
  const flash = (text: string) => { setToast(text); setTimeout(() => setToast(""), 1800); };

  const call = useCallback(async (path: string, init: RequestInit = {}) => {
    const r = await fetch(`/api/study/admin${path}`, {
      ...init, headers: { "content-type": "application/json", "x-admin-token": token, ...(init.headers || {}) },
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      // FastAPI validation errors arrive as a list; show the first one readably
      const d = body.detail;
      const text = typeof d === "string" ? d
        : Array.isArray(d) && d[0] ? `${(d[0].loc ?? []).slice(-1)[0] ?? "value"}: ${d[0].msg}` : `Error ${r.status}`;
      throw new Error(text);
    }
    return body;
  }, [token]);

  const refresh = useCallback(async () => {
    const [d, sm] = await Promise.all([
      call("/studies"),
      call(`/summary${filter ? `?study=${encodeURIComponent(filter)}` : ""}`),
    ]);
    setStudies(d.studies); setEngines(d.engines); setSummary(sm);
  }, [call, filter]);

  useEffect(() => { try { const t = sessionStorage.getItem("admin_token"); if (t) setToken(t); } catch {} }, []);
  useEffect(() => {
    if (!authed) return;
    setBusy("data");
    refresh().catch((e) => setMsg(e.message)).finally(() => setBusy(null));
  }, [authed, filter, refresh]);

  async function login() {
    setMsg(""); setBusy("login");
    try { await call("/studies"); setAuthed(true); try { sessionStorage.setItem("admin_token", token); } catch {} }
    catch { setMsg("Wrong token, or STUDY_ADMIN_TOKEN is not set on the API."); }
    finally { setBusy(null); }
  }

  async function save() {
    if (!editing) return;
    setMsg("");
    if (isNew && editing.id && !/^[a-z0-9][a-z0-9-]{2,39}$/.test(editing.id)) {
      setMsg("Study ID: 3–40 characters, lowercase letters, digits and hyphens only (e.g. ramadan-pilot). Or leave it empty for an automatic one.");
      return;
    }
    setBusy("save");
    const body = { ...editing, id: isNew ? (editing.id || undefined) : undefined };
    try {
      if (isNew) await call("/studies", { method: "POST", body: JSON.stringify(body) });
      else await call(`/studies/${editing.id}`, { method: "PATCH", body: JSON.stringify(body) });
      setEditing(null); flash(isNew ? "Study created" : "Saved"); await refresh();
    } catch (e) { setMsg((e as Error).message); }
    finally { setBusy(null); }
  }

  async function setStatus(s: Study, status: Study["status"]) {
    setMsg("");
    // show the new status at once; put it back if the server refuses
    setStudies((all) => all.map((x) => (x.id === s.id ? { ...x, status } : x)));
    setBusy(`status:${s.id}`);
    try {
      await call(`/studies/${s.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      flash(`“${s.name}” is now ${status}`);
      void refresh();
    } catch (e) {
      setStudies((all) => all.map((x) => (x.id === s.id ? { ...x, status: s.status } : x)));
      setMsg((e as Error).message);
    } finally { setBusy(null); }
  }

  async function preview(s: Study) {
    setMsg(""); setBusy(`preview:${s.id}`);
    try {
      const { url } = await call(`/studies/${s.id}/preview`, { method: "POST" });
      try { for (const k of Object.keys(sessionStorage)) if (k.startsWith("study_turns_")) sessionStorage.removeItem(k); } catch {}
      window.location.href = url;          // same tab; "Exit preview" brings you back here
    } catch (e) { setMsg((e as Error).message); setBusy(null); }
  }

  async function remove(s: Study) {
    if (!confirm(`Delete study "${s.name}"? This only works while it has no participants.`)) return;
    setBusy(`delete:${s.id}`);
    try { await call(`/studies/${s.id}`, { method: "DELETE" }); flash("Study deleted"); await refresh(); }
    catch (e) { setMsg((e as Error).message); }
    finally { setBusy(null); }
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
        <button disabled={busy === "login"} className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 font-semibold text-white disabled:opacity-70">
          {busy === "login" && <span className="spinner" />} Sign in
        </button>
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
      {toast && (
        <div role="status" className="rise fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full bg-ink px-5 py-2.5 text-white shadow-lg">
          ✓ {toast}
        </div>
      )}

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
                <tr key={s.id} className={`border-t border-line align-top transition-opacity ${busy === `delete:${s.id}` ? "opacity-40" : ""}`}>
                  <td className="px-3 py-3"><div className="font-semibold">{s.name}</div><div className="font-mono text-[12px] text-muted">{s.id}</div></td>
                  <td className="px-3 py-3">{MODES[s.mode].label}</td>
                  <td className="px-3 py-3">{s.wallet.toLocaleString()}</td>
                  <td className="px-3 py-3">{s.mode === "browse" ? "—" : s.maxTurns}</td>
                  <td className="px-3 py-3">{[s.preSurvey && "pre", s.postSurvey && "post"].filter(Boolean).join(" + ") || "none"}</td>
                  <td className="px-3 py-3">{n(s)}{n(s) > 0 && <div className="text-[12px] text-muted">{Object.entries(s.participants).map(([k, v]) => `${k} ${v}`).join(" · ")}</div>}</td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2">
                      <select value={s.status} disabled={busy === `status:${s.id}`}
                        onChange={(e) => setStatus(s, e.target.value as Study["status"])}
                        className={`rounded-md border px-2 py-1 disabled:opacity-60 ${s.status === "open" ? "border-brand-500 text-brand-700" : "border-line"}`}>
                        <option value="draft">draft</option><option value="open">open</option><option value="closed">closed</option>
                      </select>
                      {busy === `status:${s.id}` && <span className="flex items-center gap-1 text-[12px] text-muted"><span className="spinner" /> saving…</span>}
                    </div>
                  </td>
                  <td className="px-3 py-3"><button onClick={() => copy(s.id)} className="text-brand-600 hover:underline">{copied === s.id ? "copied ✓" : "copy link"}</button></td>
                  <td className="px-3 py-3 text-right">
                    <button onClick={() => preview(s)} disabled={!!busy}
                      className="me-3 inline-flex items-center gap-1 font-semibold text-brand-600 hover:underline">
                      {busy === `preview:${s.id}` && <span className="spinner" />}preview
                    </button>
                    <button onClick={() => { setIsNew(false); setEditing({ ...s }); setMsg(""); }} className="text-brand-600 hover:underline">edit</button>
                    {n(s) === 0 && <button onClick={() => remove(s)} className="ms-3 text-muted hover:text-ember-600">delete</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[12.5px] text-muted">Only <b>open</b> studies accept participants. Once a study has participants its design is locked; to change it, create a new study.
          <b> Preview</b> lets you go through any study (drafts too) as a participant; preview runs are never counted in the data.</p>
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
            <button onClick={save} disabled={busy === "save"}
              className="flex items-center gap-2 rounded-lg bg-brand-500 px-5 py-2 font-semibold text-white disabled:opacity-70">
              {busy === "save" && <span className="spinner" />}{busy === "save" ? "Saving…" : isNew ? "Create (as draft)" : "Save"}
            </button>
            <button onClick={() => setEditing(null)} className="rounded-lg border border-line px-5 py-2">Cancel</button>
          </div>
        </section>
      )}

      {/* -------------------------------------------------------------- data */}
      <section className="mt-10">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold">Data</h2>
          {busy === "data" && <span className="spinner text-brand-500" />}
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
