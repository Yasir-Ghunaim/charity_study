"use client";
import { useEffect } from "react";
import { study } from "@/lib/client";

/** Logs how long a campaign page was actually visible. */
export function DwellTracker({ campaignId }: { campaignId: string }) {
  useEffect(() => {
    let visibleSince = document.visibilityState === "visible" ? Date.now() : 0;
    let total = 0;
    const onVis = () => {
      if (document.visibilityState === "hidden" && visibleSince) { total += Date.now() - visibleSince; visibleSince = 0; }
      else if (document.visibilityState === "visible") visibleSince = Date.now();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      if (visibleSince) total += Date.now() - visibleSince;
      study.log("detail_dwell", campaignId, { ms: total });
    };
  }, [campaignId]);
  return null;
}
