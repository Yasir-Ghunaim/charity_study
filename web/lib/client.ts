"use client";
// Browser-side calls. Same-origin /api/* is proxied to FastAPI; the participant
// cookie travels with every request, so no id is ever sent from the page.
import type { AgentEvent, Wallet } from "./types";

async function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method, headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let msg = `${res.status}`;
    try { msg = (await res.json()).detail ?? msg; } catch {}
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const study = {
  join: (b: { studyId: string; nickname: string; lang: string; adult: boolean; consent: boolean; consentVersion: string }) =>
    send<{ ok: boolean; code: string }>("/study/join", "POST", b),
  survey: (phase: string, answers: Record<string, unknown>) => send("/study/survey/" + phase, "POST", { answers }),
  me: () => send<{ wallet: Wallet }>("/study/me", "GET"),
  allocate: (campaignId: string, amount: number, source: string) =>
    send<Wallet>("/study/allocations", "POST", { campaignId, amount, source }),
  allocateBatch: (items: { campaignId: string; amount: number; source: string }[]) =>
    send<Wallet>("/study/allocations/batch", "POST", { items }),
  finish: () => send("/study/finish", "POST"),
  log: (type: string, campaignId?: string, payload?: object) => {
    const body = JSON.stringify({ type, campaignId, payload, clientTs: new Date().toISOString() });
    if (navigator.sendBeacon) navigator.sendBeacon("/api/study/events", new Blob([body], { type: "application/json" }));
    else void fetch("/api/study/events", { method: "POST", headers: { "content-type": "application/json" }, body, keepalive: true });
  },
};

/** Stream agent events (server-sent events over a POST). Throws Error("429") at the message limit. */
export async function streamAgent(message: string, history: { role: string; content: string }[],
  onEvent: (e: AgentEvent) => void) {
  const res = await fetch("/api/study/agent", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ message, history }),
  });
  if (!res.ok || !res.body) throw new Error(String(res.status));
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
      for (const line of chunk.split("\n")) if (line.startsWith("data: ")) onEvent(JSON.parse(line.slice(6)));
    }
  }
}
