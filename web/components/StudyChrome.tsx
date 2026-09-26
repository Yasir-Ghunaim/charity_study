"use client";
import { BRAND } from "@/lib/brand";
import { useLang } from "@/lib/lang";
import { useWallet } from "@/lib/wallet";
import { LangIcon } from "./Icons";

export function StudyHeader({ step }: { step?: 1 | 2 | 3 }) {
  const { lang, t, setLang, switching } = useLang();
  const w = useWallet();
  const labels = [t("stepPre"), t("stepTask"), t("stepPost")];
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="text-[19px] font-bold text-[#1d3f5e]">{BRAND[lang]}</span>
          <span className="rounded-full border border-brand-300 px-2.5 py-0.5 text-[12px] text-brand-600">{t("studyBadge")}</span>
        </div>
        {step && (
          <div className="hidden items-center gap-2 text-[12.5px] text-muted md:flex">
            <span>{t("step", { n: step })}</span><span className="text-ink">·</span><span className="text-ink">{labels[step - 1]}</span>
          </div>
        )}
        <div className="ms-auto flex items-center gap-4">
          {w && step === 2 && (
            <div className="rounded-full bg-brand-50 px-3.5 py-1.5 text-[13.5px] text-brand-700">
              {t("walletLabel")}: <b className="num">{Math.round(w.wallet.remaining).toLocaleString("en-US")}</b>{" "}
              <span className="text-muted">{t("of")} <span className="num">{w.wallet.start.toLocaleString("en-US")}</span></span>
            </div>
          )}
          <button onClick={() => setLang(lang === "ar" ? "en" : "ar")} disabled={switching} aria-busy={switching}
            className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[14px] hover:bg-panel hover:text-brand-600 disabled:opacity-70">
            {switching ? <span className="spinner text-brand-500" /> : <LangIcon size={18} />} {t("switchLang")}
          </button>
        </div>
      </div>
    </header>
  );
}

export function StudyFooter({ code }: { code?: string }) {
  const { t } = useLang();
  return (
    <footer className="mt-16 border-t border-line">
      <div className="mx-auto max-w-[1200px] px-5 py-5 text-[12.5px] text-muted">
        {t("brandTag")}{code && <> · {t("codeLine")}: <b className="num text-ink">{code}</b></>}
      </div>
    </footer>
  );
}
