import { notFound, redirect } from "next/navigation";
import { Consent } from "@/components/Consent";
import { Notice } from "@/components/Notice";
import { StudyFooter, StudyHeader } from "@/components/StudyChrome";
import { SwitchStudy } from "@/components/SwitchStudy";
import { api, getLang, routeFor } from "@/lib/api";
import { translate } from "@/lib/i18n";

// Participant link for one study: /s/<study id>
//  - already in this study      -> resume where they are (or the thank-you page)
//  - finished another study     -> may join this one as a new participant
//  - midway through another one -> choose: continue it, or join this one instead
export default async function StudyLink({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [me, study, lang] = await Promise.all([api.me(), api.study(id), getLang()]);
  if (!study) notFound();
  if (me && me.study.id === id) redirect(routeFor(me));

  const accepting = study.status === "open" || study.preview;
  let body: React.ReactNode;
  if (!accepting) body = <Notice text={translate(lang, study.status === "draft" ? "studyDraft" : "studyClosed")} />;
  else if (me && me.status !== "completed" && !study.preview) body = <SwitchStudy study={study} continueHref={routeFor(me)} />;
  else body = <Consent study={study} />;

  return (
    <>
      <StudyHeader />
      <main className="mx-auto max-w-3xl px-5 py-8">{body}</main>
      <StudyFooter />
    </>
  );
}
