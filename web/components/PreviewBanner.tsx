"use client";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useLang } from "@/lib/lang";

/** Shown on every page while the admin previews a study. */
export function PreviewBanner() {
  const { t } = useLang();
  const path = usePathname();
  const [busy, setBusy] = useState<"restart" | "exit" | null>(null);
  if (path.startsWith("/admin")) return null;

  async function go(action: "restart" | "exit") {
    setBusy(action);
    try {
      const r = await fetch(`/api/study/preview/${action}`, { method: "POST" });
      const { url } = await r.json();
      try {
        for (const k of Object.keys(sessionStorage)) if (k.startsWith("study_turns_")) sessionStorage.removeItem(k);
      } catch {}
      window.location.href = url ?? "/admin";      // full reload: the session cookies just changed
    } catch { setBusy(null); }
  }

  return (
    <div className="bg-[#fff4d6] text-[#5c4300]">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-4 gap-y-2 px-5 py-2 text-[13.5px]">
        <span className="rounded-full bg-[#5c4300] px-2.5 py-0.5 text-[12px] font-semibold text-white">{t("previewMode")}</span>
        <span className="flex-1">{t("previewNote")}</span>
        <button onClick={() => go("restart")} disabled={!!busy}
          className="flex items-center gap-1.5 rounded-lg border border-[#5c4300]/30 px-3 py-1 font-semibold hover:bg-white/60">
          {busy === "restart" && <span className="spinner" />}{t("previewRestart")}
        </button>
        <button onClick={() => go("exit")} disabled={!!busy}
          className="flex items-center gap-1.5 rounded-lg bg-[#5c4300] px-3 py-1 font-semibold text-white hover:opacity-90">
          {busy === "exit" && <span className="spinner" />}{t("previewExit")}
        </button>
      </div>
    </div>
  );
}
