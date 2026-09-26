"use client";
import { useRouter } from "next/navigation";
import { createContext, useContext } from "react";
import { LANG_COOKIE, translate, type Key, type Lang } from "./i18n";

const Ctx = createContext<Lang>("ar");

export function LangProvider({ lang, children }: { lang: Lang; children: React.ReactNode }) {
  return <Ctx.Provider value={lang}>{children}</Ctx.Provider>;
}

export function useLang() {
  const lang = useContext(Ctx);
  const router = useRouter();
  const t = (key: Key, vars?: Record<string, string | number>) => translate(lang, key, vars);
  async function setLang(next: Lang) {
    document.cookie = `${LANG_COOKIE}=${next}; path=/; max-age=31536000; samesite=lax`;
    await fetch("/api/study/lang", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ lang: next }) }).catch(() => {});
    router.refresh();
  }
  return { lang, t, setLang };
}
