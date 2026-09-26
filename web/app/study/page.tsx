import { redirect } from "next/navigation";
import { StudyFooter, StudyHeader } from "@/components/StudyChrome";
import { StudyWorkspace } from "@/components/StudyWorkspace";
import { WalletPanel } from "@/components/WalletPanel";
import { api, routeFor } from "@/lib/api";
import { WalletProvider } from "@/lib/wallet";

export default async function StudyPage() {
  const me = await api.me();
  if (!me) redirect("/");
  if (me.status !== "pre_done") redirect(routeFor(me));
  return (
    <WalletProvider initial={me.wallet} enabled>
      <StudyHeader step={2} />
      <main className="mx-auto grid max-w-[1200px] gap-6 px-5 py-8 lg:grid-cols-[1fr_300px]">
        <StudyWorkspace me={me} />
        <WalletPanel />
      </main>
      <StudyFooter code={me.code} />
    </WalletProvider>
  );
}
