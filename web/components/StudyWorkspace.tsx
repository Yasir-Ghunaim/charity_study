"use client";
import { useState } from "react";
import { study } from "@/lib/client";
import { useLang } from "@/lib/lang";
import type { Participant } from "@/lib/types";
import { AgentConversation } from "./AgentConversation";
import { BrowsePanel } from "./BrowsePanel";
import { ChatIcon, SearchIcon } from "./Icons";

/** Lays out the allocation step according to the study's interface. */
export function StudyWorkspace({ me }: { me: Participant }) {
  const { t } = useLang();
  const { assistant, browse } = me.study;
  const [tab, setTab] = useState<"assistant" | "browse">(assistant ? "assistant" : "browse");
  const agent = <AgentConversation code={me.code} wallet={me.wallet.start} />;
  const explorer = <BrowsePanel wallet={me.wallet.start} />;
  if (!(assistant && browse)) return assistant ? agent : explorer;

  const pick = (next: "assistant" | "browse") => {
    if (next !== tab) study.log("tab_switch", undefined, { from: tab, to: next });
    setTab(next);
  };
  const cls = (on: boolean) =>
    `flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-[15px] font-semibold ${on ? "bg-white text-brand-700 shadow" : "text-muted hover:text-ink"}`;
  return (
    <div>
      <div className="mb-4 flex gap-1 rounded-2xl bg-panel p-1 ring-1 ring-line">
        <button onClick={() => pick("assistant")} className={cls(tab === "assistant")}><ChatIcon size={18} /> {t("tabAssistant")}</button>
        <button onClick={() => pick("browse")} className={cls(tab === "browse")}><SearchIcon size={18} /> {t("tabBrowse")}</button>
      </div>
      {/* both stay mounted so neither loses its state when switching */}
      <div hidden={tab !== "assistant"}>{agent}</div>
      <div hidden={tab !== "browse"}>{explorer}</div>
    </div>
  );
}
