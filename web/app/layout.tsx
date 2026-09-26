import type { Metadata } from "next";
import { Amiri, IBM_Plex_Sans_Arabic } from "next/font/google";
import { cookies } from "next/headers";
import { PreviewBanner } from "@/components/PreviewBanner";
import { getLang } from "@/lib/api";
import { LangProvider } from "@/lib/lang";
import "./globals.css";

const plex = IBM_Plex_Sans_Arabic({ subsets: ["arabic", "latin"], weight: ["400", "500", "600", "700"], variable: "--font-plex", display: "swap" });
const amiri = Amiri({ subsets: ["arabic"], weight: ["400", "700"], variable: "--font-amiri", display: "swap" });

export const metadata: Metadata = {
  title: "دراسة العطاء · Giving Study",
  description: "Research study on how people choose charity campaigns",
  robots: { index: false, follow: false },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const [lang, jar] = await Promise.all([getLang(), cookies()]);
  const previewing = jar.has("study_preview");
  return (
    <html lang={lang} dir={lang === "ar" ? "rtl" : "ltr"} className={`${plex.variable} ${amiri.variable}`}>
      <body className="min-h-screen bg-[#fafbfa]">
        <LangProvider lang={lang}>{previewing && <PreviewBanner />}{children}</LangProvider>
      </body>
    </html>
  );
}
