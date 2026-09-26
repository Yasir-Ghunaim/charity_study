import { redirect } from "next/navigation";
import { StudyFooter, StudyHeader } from "@/components/StudyChrome";
import { api, getLang, routeFor } from "@/lib/api";
import { translate } from "@/lib/i18n";

export default async function Done() {
  const [me, lang] = await Promise.all([api.me(), getLang()]);
  if (!me) redirect("/");
  if (me.status !== "completed") redirect(routeFor(me));
  const t = (k: Parameters<typeof translate>[1]) => translate(lang, k);
  return (
    <>
      <StudyHeader />
      <main className="mx-auto max-w-xl px-5 py-16 text-center">
        <div className="text-[30px] font-bold">{t("thanks")}</div>
        <p className="mt-3 text-[15.5px] leading-8 text-muted">{t("thanksBody")}</p>
        <div className="mt-8 rounded-2xl border border-line bg-white p-6">
          <div className="text-[14px] text-muted">{t("codeLine")}</div>
          <div className="num mt-1 text-[32px] font-bold tracking-widest text-brand-600">{me.code}</div>
          <div className="mt-2 text-[13px] text-muted">{t("codeHint")}</div>
        </div>
      </main>
      <StudyFooter code={me.code} />
    </>
  );
}
