import { notFound, redirect } from "next/navigation";
import { StudyFooter, StudyHeader } from "@/components/StudyChrome";
import { SurveyForm } from "@/components/SurveyForm";
import { api, getLang, routeFor } from "@/lib/api";
import { translate } from "@/lib/i18n";

export default async function SurveyPage({ params }: { params: Promise<{ phase: string }> }) {
  const { phase } = await params;
  if (phase !== "pre" && phase !== "post") notFound();
  const me = await api.me();
  if (!me) redirect("/");
  if (routeFor(me) !== `/survey/${phase}`) redirect(routeFor(me));
  const [survey, lang] = await Promise.all([api.survey(phase), getLang()]);
  if (!survey) notFound();
  const t = (k: Parameters<typeof translate>[1]) => translate(lang, k);
  return (
    <>
      <StudyHeader step={phase === "pre" ? 1 : 3} />
      <main className="mx-auto max-w-3xl px-5 py-8">
        <h1 className="text-[26px] font-bold">{phase === "pre" ? t("preTitle") : t("postTitle")}</h1>
        <p className="mb-6 mt-1 text-[14.5px] text-muted">{phase === "pre" ? t("preIntro") : t("postIntro")}</p>
        <SurveyForm survey={survey} next={phase === "pre" ? "/study" : "/done"} />
      </main>
      <StudyFooter code={me.code} />
    </>
  );
}
