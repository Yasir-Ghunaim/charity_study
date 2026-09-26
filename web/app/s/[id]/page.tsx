import { notFound, redirect } from "next/navigation";
import { Consent } from "@/components/Consent";
import { Notice } from "@/components/Notice";
import { StudyFooter, StudyHeader } from "@/components/StudyChrome";
import { api, getLang, routeFor } from "@/lib/api";
import { translate } from "@/lib/i18n";

// Participant link for one study: /s/<study id>
export default async function StudyLink({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [me, study, lang] = await Promise.all([api.me(), api.study(id), getLang()]);
  if (me) redirect(routeFor(me));
  if (!study) notFound();
  return (
    <>
      <StudyHeader />
      <main className="mx-auto max-w-3xl px-5 py-8">
        {study.status === "open" ? <Consent study={study} />
          : <Notice text={translate(lang, study.status === "draft" ? "studyDraft" : "studyClosed")} />}
      </main>
      <StudyFooter />
    </>
  );
}
