import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { AllocationControl } from "@/components/AllocationControl";
import { CampaignCover } from "@/components/CampaignCover";
import { DwellTracker } from "@/components/DwellTracker";
import { Progress } from "@/components/Progress";
import { Amount } from "@/components/Riyal";
import { StudyFooter, StudyHeader } from "@/components/StudyChrome";
import { WalletPanel } from "@/components/WalletPanel";
import { api, getLang, routeFor } from "@/lib/api";
import { pick, translate } from "@/lib/i18n";
import { WalletProvider } from "@/lib/wallet";

export default async function CampaignPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [me, c, lang] = await Promise.all([api.me(), api.campaign(id), getLang()]);
  if (!me) redirect("/");
  if (me.status !== "pre_done") redirect(routeFor(me));
  if (!c) notFound();
  const t = (k: Parameters<typeof translate>[1], v?: Record<string, string | number>) => translate(lang, k, v);
  const cp = c.charityProfile;
  const stats: [string, React.ReactNode][] = [
    [t("raised"), <Amount key="r" value={c.raisedAmount} />],
    [t("remaining"), <Amount key="m" value={c.remainingAmount} />],
    [t("goal"), <Amount key="g" value={c.goalAmount} />],
    [t("beneficiaries"), <span key="b" className="num">{c.beneficiaries.toLocaleString("en-US")}</span>],
    [t("region"), pick(lang, c, "region", "regionEn")],
    ...(c.unitCost ? [[t("unit"), <span key="u">{pick(lang, c, "unitAr", "unitEn")} · <Amount value={c.unitCost} /></span>] as [string, React.ReactNode]] : []),
    ...(c.zakatCategory ? [[t("zakatCategory"), pick(lang, c, "zakatCategory", "zakatCategoryEn")] as [string, React.ReactNode]] : []),
    ...(cp ? [[t("compareGov"), <span key="gv" className="num">{cp.governanceScore}/100</span>] as [string, React.ReactNode],
              [t("compareOverhead"), <span key="oh" className="num">{cp.overheadPct}%</span>] as [string, React.ReactNode],
              [t("compareAudit"), cp.auditedYear ?? t("notPublished")] as [string, React.ReactNode]] : []),
  ];
  return (
    <WalletProvider initial={me.wallet} enabled>
      <StudyHeader step={2} />
      <DwellTracker campaignId={c.id} />
      <main className="mx-auto max-w-[1200px] px-5 py-6">
        <Link href="/study" className="text-[14px] text-brand-600 hover:underline">{lang === "ar" ? "→" : "←"} {t("back")}</Link>
        <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_300px]">
          <div>
            <div className="overflow-hidden rounded-2xl">
              <CampaignCover id={c.id} hue={c.hue} glyph={c.glyph} big className="aspect-[400/170] w-full" />
              <Progress value={c.progressPct} className="h-8 rounded-b-2xl" />
            </div>
            <div className="mt-5 flex flex-wrap gap-2 text-[13px]">
              <span className="rounded-md border border-line px-2 py-1">{pick(lang, c, "categoryNameAr", "categoryNameEn")}</span>
              {c.isZakat && <span className="rounded-md bg-brand-50 px-2 py-1 text-brand-700">{t("zakat")}</span>}
              {c.isWaqf && <span className="rounded-md bg-brand-50 px-2 py-1 text-brand-700">{t("compareWaqf")}</span>}
              {c.nearComplete && <span className="rounded-md bg-ember-500 px-2 py-1 text-white">{t("almostFunded")}</span>}
            </div>
            <h1 className="mt-3 text-[28px] font-bold text-brand-600">{pick(lang, c, "titleAr", "titleEn")}</h1>
            <div className="text-[14px] text-muted">{pick(lang, c, "charity", "charityEn")}</div>
            <p className="mt-4 text-[16px] leading-8">{pick(lang, c, "descriptionAr", "descriptionEn")}</p>
            <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3">
              {stats.map(([k, v]) => (
                <div key={k} className="rounded-xl bg-white px-4 py-3 ring-1 ring-line">
                  <div className="text-[12.5px] text-brand-600">{k}</div>
                  <div className="mt-0.5 text-[16px] font-bold">{v}</div>
                </div>
              ))}
            </div>
            {!!c.updates?.length && (
              <div className="mt-6">
                <h2 className="text-[16px] font-semibold">{t("updates")}</h2>
                <ul className="mt-2 space-y-2">
                  {c.updates.map((u, i) => (
                    <li key={i} className="rounded-xl bg-white px-4 py-2.5 text-[14px] ring-1 ring-line">
                      <span className="num me-2 text-[12px] text-muted">{u.createdAt.slice(0, 10)}</span>{lang === "en" ? u.textEn : u.textAr}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl border border-line bg-white p-5">
              <div className="mb-3 text-[15px] font-semibold">{t("allocateHere")}</div>
              <AllocationControl c={c} source="detail" big />
            </div>
            <WalletPanel />
          </div>
        </div>
      </main>
      <StudyFooter code={me.code} />
    </WalletProvider>
  );
}
