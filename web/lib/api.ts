// Server-side data access. Forwards the participant cookie to FastAPI.
import "server-only";
import { cookies } from "next/headers";
import { LANG_COOKIE, type Lang } from "./i18n";
import type { Campaign, Participant, StudyPublic, Survey } from "./types";

const API = process.env.API_URL ?? "http://127.0.0.1:8000";

async function get<T>(path: string): Promise<{ status: number; data: T | null }> {
  const jar = await cookies();
  const res = await fetch(`${API}/api${path}`, {
    cache: "no-store",
    headers: { cookie: jar.getAll().map((c) => `${c.name}=${c.value}`).join("; ") },
  });
  return { status: res.status, data: res.ok ? ((await res.json()) as T) : null };
}

export async function getLang(): Promise<Lang> {
  const v = (await cookies()).get(LANG_COOKIE)?.value;
  return v === "en" ? "en" : "ar";
}

export const api = {
  me: async () => (await get<Participant>("/study/me")).data,
  study: async (id: string) => (await get<StudyPublic>(`/study/s/${encodeURIComponent(id)}`)).data,
  openStudies: async () => (await get<{ open: string[] }>("/study/open")).data?.open ?? [],
  survey: async (phase: string) => (await get<Survey>(`/study/survey/${phase}`)).data,
  campaign: async (id: string) => (await get<Campaign & { updates?: { textAr: string; textEn: string; createdAt: string }[] }>(
    `/campaigns/${encodeURIComponent(id)}`)).data,
};

/** Where a participant belongs, given their status. */
export function routeFor(p: Participant | null): string {
  if (!p) return "/";
  return { consented: "/survey/pre", pre_done: "/study", finished: "/survey/post", completed: "/done" }[p.status] ?? "/";
}
