export type Campaign = {
  id: string;
  titleAr: string; titleEn: string;
  descriptionAr: string; descriptionEn: string;
  categoryId: string; categoryNameAr: string; categoryNameEn: string;
  hue: number; glyph: string; tags: string[];
  goalAmount: number; raisedAmount: number; remainingAmount: number; progressPct: number;
  beneficiaries: number;
  region: string; regionEn: string;
  charity: string; charityEn: string | null; charityId: string | null;
  unitAr: string | null; unitEn: string | null; unitCost: number | null;
  zakatCategory: string | null; zakatCategoryEn: string | null;
  isZakat: boolean; isWaqf: boolean; minDonation: number;
  createdAt: string; endsAt: string | null; status: string; nearComplete: boolean;
  updates?: { textAr: string; textEn: string; createdAt: string }[];
  charityProfile?: { governanceScore: number; overheadPct: number; auditedYear: number | null; foundedYear: number } | null;
};

export type Wallet = { start: number; allocated: number; remaining: number; items: { campaign: Campaign; amount: number }[] };

export type Mode = "assistant" | "assistant_browse" | "browse";

export type Participant = {
  code: string; nickname: string; lang: "ar" | "en";
  status: "consented" | "pre_done" | "finished" | "completed"; wallet: Wallet;
  study: { id: string | null; mode: Mode; maxTurns: number; preSurvey: boolean; postSurvey: boolean; assistant: boolean; browse: boolean };
};

export type ConsentText = { title: string; sections: { heading: string; body: string }[]; checks: string[] };

export type StudyPublic = {
  id: string; status: "draft" | "open" | "closed"; mode: Mode; wallet: number; maxTurns: number;
  preSurvey: boolean; postSurvey: boolean;
  consent: { version: string; ar: ConsentText; en: ConsentText };
};

export type Category = { id: string; nameAr: string; nameEn: string; glyph: string; hue: number; campaignCount: number };

export type Option = { value: string | number; ar: string; en: string };
export type Question = { id: string; type: "single" | "multi" | "likert" | "text"; required: boolean; ar: string; en: string; options?: Option[] };
export type Survey = { phase: string; version: string; questions: Question[] };

export type CompareRow = {
  campaign_id: string; title: string; charity: string; region: string; progress_pct: number;
  remaining_sar: number; unit: string | null; unit_cost_sar: number | null; zakat_eligible: boolean; waqf: boolean;
  charity_governance_score: number | null; charity_overhead_pct: number | null;
  charity_audited_year: number | null; charity_founded: number | null;
};

export type Impact = {
  amount_sar: number; unit: string | null; units_funded: number | null; share_of_remaining_pct: number;
  would_complete_campaign: boolean; remaining_after_sar: number; estimated_annual_yield_sar?: number;
};

export type UIBlock =
  | { kind: "campaigns"; heading: string; campaigns: Campaign[] }
  | { kind: "comparison"; rows: CompareRow[]; campaigns: Campaign[];
      alternatives?: { categoryId: string; categoryAr: string; categoryEn: string; campaigns: Campaign[] }[] }
  | { kind: "impact"; campaign: Campaign; impact: Impact }
  | { kind: "allocation"; note: string; total: number; items: { campaign: Campaign; amount: number; units: number | null }[] };

export type AgentEvent =
  | { type: "start"; engine: string; model: string | null }
  | { type: "step"; tool: string; labelAr: string; labelEn: string; input: Record<string, unknown> }
  | { type: "ui"; block: UIBlock; auto?: boolean }
  | { type: "text"; text: string }
  | { type: "error"; message: string }
  | { type: "done"; engine: string; model: string | null };
