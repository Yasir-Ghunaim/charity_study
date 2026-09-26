import { redirect } from "next/navigation";
import { Notice } from "@/components/Notice";
import { StudyFooter, StudyHeader } from "@/components/StudyChrome";
import { api, getLang, routeFor } from "@/lib/api";
import { translate } from "@/lib/i18n";

// The bare site address: a returning participant resumes where they were; a
// newcomer is sent to the study when exactly one is open.
export default async function Start() {
  const [me, open, lang] = await Promise.all([api.me(), api.openStudies(), getLang()]);
  if (me) redirect(routeFor(me));
  if (open.length === 1) redirect(`/s/${open[0]}`);
  return (
    <>
      <StudyHeader />
      <main className="mx-auto max-w-2xl px-5 py-16"><Notice text={translate(lang, "noStudy")} /></main>
      <StudyFooter />
    </>
  );
}
