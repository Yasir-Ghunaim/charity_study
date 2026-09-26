export type Lang = "ar" | "en";
export const LANG_COOKIE = "study_lang";

const ar = {
  studyBadge: "دراسة بحثية", switchLang: "English", brandTag: "المال في هذه الدراسة افتراضي بالكامل",
  // consent
  nicknameLabel: "اختر اسماً مستعاراً", nicknameHint: "لا تستخدم اسمك الحقيقي.", start: "أوافق وأبدأ",
  consentNeeded: "يلزم تأكيد العمر والموافقة للمتابعة.", nicknameNeeded: "اكتب اسماً مستعاراً من حرفين على الأقل.",
  // steps
  step: "الخطوة {n} من 3", stepPre: "أسئلة تمهيدية", stepTask: "توزيع الرصيد", stepPost: "أسئلة ختامية",
  // surveys
  preTitle: "قبل أن نبدأ", preIntro: "أسئلة قصيرة عنك وعن عادات عطائك. لا توجد إجابات صحيحة أو خاطئة.",
  postTitle: "أسئلة ختامية", postIntro: "أخبرنا عن تجربتك مع المساعد.", optional: "اختياري",
  continue: "متابعة", answerRequired: "أجب عن الأسئلة المطلوبة (المعلّمة بنجمة).", sending: "جاري الإرسال…",
  // study
  heading: "ما الذي تريد دعمه اليوم؟",
  intro: "لديك {wallet} ريال افتراضي. أخبر المساعد بما يهمّك: قضية، أو فئة من المحتاجين، أو نوع العطاء. سيبحث لك في الفرص ويقارن بينها، ثم توزّع رصيدك بنفسك من البطاقات.",
  walletLabel: "رصيدك الافتراضي", left: "متبقٍ", of: "من", allocatedTo: "خصّصت لـ {n} فرص",
  yourAllocations: "توزيعك", noAllocations: "لم تخصّص شيئاً بعد.",
  finish: "إنهاء التوزيع", finishConfirm: "هل انتهيت من توزيع رصيدك؟ لن تتمكن من التعديل بعدها.",
  finishLeftover: "بقي {n} ريال افتراضي دون تخصيص. هل تريد الإنهاء على أي حال؟", finishNeedOne: "خصّص لفرصة واحدة على الأقل قبل الإنهاء.",
  ask: "اسأل", askPlaceholder: "مثال: أريد مساعدة مرضى الكلى", followPlaceholder: "اكتب سؤالاً آخر…",
  searching: "جاري البحث", stepsDone: "عدد الخطوات: {n}", showSteps: "عرض الخطوات", hideSteps: "إخفاء",
  limitReached: "بلغت الحد الأقصى للرسائل في هذه الدراسة. يمكنك إكمال التوزيع من البطاقات ثم الإنهاء.",
  serverError: "تعذّر الاتصال بالخادم. حاول مرة أخرى.", techNote: "تنبيه تقني",
  starters: "عندي 300 ريال زكاة وأريد أن تذهب للأيتام|أريد صدقة جارية عن والدتي المتوفاة|ما الفرص التي تحتاج دعماً عاجلاً؟|قارن لي بين حفر الآبار ووقف السقيا|أريد مساعدة أطفال لا يسمعون",
  // card
  raised: "تم جمع", remaining: "المبلغ المتبقي", amount: "المبلغ", allocate: "خصّص", update: "تحديث", remove: "إزالة",
  allocatedHere: "خصّصت هنا", details: "عرض التفاصيل", almostFunded: "شارفت على الاكتمال", zakat: "تقبل الزكاة",
  minAmount: "أقل مبلغ {n}", notEnough: "الرصيد لا يكفي (متبقٍ {n})", saved: "تم الحفظ",
  // blocks
  compareCharity: "الجهة المنفذة", compareRegion: "المنطقة", compareProgress: "نسبة الإنجاز", compareRemaining: "المبلغ المتبقي",
  compareUnit: "وحدة الأثر", compareZakat: "تقبل الزكاة", compareWaqf: "وقف", compareGov: "مؤشر حوكمة الجهة",
  compareOverhead: "المصاريف الإدارية", compareAudit: "آخر قوائم مالية مدققة", yes: "نعم", no: "لا", notPublished: "غير منشورة",
  allocateEither: "خصّص لأيٍّ من الخيارين", moreIn: "فرص أخرى في مجال {c}",
  suggestedSplit: "توزيع مقترح", acceptSplit: "خصّص هذا التوزيع", total: "الإجمالي", splitDone: "تم التخصيص",
  impactWith: "بمبلغ {a} في", ofRemaining: "من المبلغ المتبقي", completes: "يكمل الفرصة", annualYield: "ريع سنوي تقديري",
  // detail
  back: "العودة إلى الدراسة", goal: "المستهدف", beneficiaries: "المستفيدون", region: "المنطقة", unit: "وحدة الأثر",
  zakatCategory: "مصرف الزكاة", updates: "آخر التحديثات", allocateHere: "خصّص من رصيدك لهذه الفرصة",
  // done + footer
  tabAssistant: "المساعد الذكي", tabBrowse: "تصفّح الفرص",
  browseTitle: "تصفّح الفرص الخيرية", browseIntro: "لديك {wallet} ريال افتراضي. ابحث في الفرص وتصفّحها، ثم وزّع رصيدك بنفسك من البطاقات.",
  searchPlaceholder: "ابحث عن فرصة… (مثال: أيتام، سقيا، مرضى)", search: "بحث", all: "الكل",
  sortBy: "ترتيب", sortRelevance: "الأقرب لبحثك", sortPopular: "الأكثر تفاعلاً", sortProgress: "الأقرب للاكتمال", sortNewest: "الأحدث",
  onlyZakat: "تقبل الزكاة", onlyNearly: "شارفت على الاكتمال", results: "{n} فرصة", noResults: "لا توجد فرص مطابقة.", loadMore: "عرض المزيد",
  noStudy: "للمشاركة في الدراسة، استخدم الرابط الذي أرسله إليك الباحث.", studyDraft: "هذه الدراسة لم تبدأ بعد.",
  studyClosed: "انتهت هذه الدراسة ولم تعد تستقبل مشاركين. شكراً لاهتمامك.",
  previewMode: "وضع المعاينة", previewNote: "أنت تجرّب الدراسة كمشارك. لا يُحتسب أي شيء هنا ضمن بيانات الدراسة.",
  previewRestart: "البدء من جديد", previewExit: "إنهاء المعاينة",
  thanks: "شكراً لمشاركتك", thanksBody: "سُجّلت إجاباتك. مساهمتك تساعدنا على بناء أنظمة توصية أفضل لمنصات العمل الخيري.",
  codeLine: "رمز مشاركتك", codeHint: "احتفظ به إن أردت لاحقاً طلب حذف بياناتك.",
  virtual: "ريال افتراضي",
};

const en: typeof ar = {
  studyBadge: "Research study", switchLang: "العربية", brandTag: "All money in this study is virtual",
  nicknameLabel: "Choose a nickname", nicknameHint: "Please don't use your real name.", start: "I agree, start",
  consentNeeded: "Please confirm your age and consent to continue.", nicknameNeeded: "Enter a nickname of at least 2 characters.",
  step: "Step {n} of 3", stepPre: "Opening questions", stepTask: "Allocate your balance", stepPost: "Closing questions",
  preTitle: "Before we start", preIntro: "A few short questions about you and your giving. There are no right or wrong answers.",
  postTitle: "Closing questions", postIntro: "Tell us about your experience with the assistant.", optional: "optional",
  continue: "Continue", answerRequired: "Please answer the required questions (marked with *).", sending: "Sending…",
  heading: "What would you like to support today?",
  intro: "You have {wallet} virtual SAR. Tell the assistant what you care about: a cause, a group of people in need, or a kind of giving. It will find and compare campaigns; you allocate your balance yourself from the cards.",
  walletLabel: "Your virtual balance", left: "left", of: "of", allocatedTo: "Allocated to {n} campaigns",
  yourAllocations: "Your allocation", noAllocations: "Nothing allocated yet.",
  finish: "Finish allocating", finishConfirm: "Are you done allocating? You won't be able to change it afterwards.",
  finishLeftover: "{n} virtual SAR is still unallocated. Finish anyway?", finishNeedOne: "Allocate to at least one campaign before finishing.",
  ask: "Ask", askPlaceholder: "e.g. I want to help kidney patients", followPlaceholder: "Ask something else…",
  searching: "Searching", stepsDone: "Steps: {n}", showSteps: "Show steps", hideSteps: "Hide",
  limitReached: "You've reached the message limit for this study. You can finish allocating from the cards.",
  serverError: "Couldn't reach the server. Please try again.", techNote: "Technical note",
  starters: "I have 300 riyals of zakat for orphans|Ongoing charity (sadaqah jariyah) for my late mother|Which campaigns need urgent support?|Compare the water wells and the water endowment|I want to help children who can't hear",
  raised: "Raised", remaining: "Remaining", amount: "Amount", allocate: "Allocate", update: "Update", remove: "Remove",
  allocatedHere: "Allocated here", details: "View details", almostFunded: "Almost funded", zakat: "Zakat-eligible",
  minAmount: "Minimum {n}", notEnough: "Not enough balance ({n} left)", saved: "Saved",
  compareCharity: "Charity", compareRegion: "Region", compareProgress: "Funded", compareRemaining: "Remaining",
  compareUnit: "Impact unit", compareZakat: "Zakat-eligible", compareWaqf: "Endowment", compareGov: "Charity governance score",
  compareOverhead: "Admin overhead", compareAudit: "Latest audited accounts", yes: "Yes", no: "No", notPublished: "Not published",
  allocateEither: "Allocate to either option", moreIn: "More in {c}",
  suggestedSplit: "Suggested allocation", acceptSplit: "Allocate this split", total: "Total", splitDone: "Allocated",
  impactWith: "{a} in", ofRemaining: "of the remaining gap", completes: "Completes the campaign", annualYield: "Estimated yearly yield",
  back: "Back to the study", goal: "Goal", beneficiaries: "Beneficiaries", region: "Region", unit: "Impact unit",
  zakatCategory: "Zakat category", updates: "Latest updates", allocateHere: "Allocate from your balance",
  tabAssistant: "AI assistant", tabBrowse: "Browse campaigns",
  browseTitle: "Browse charity campaigns", browseIntro: "You have {wallet} virtual SAR. Search and browse the campaigns, then allocate your balance yourself from the cards.",
  searchPlaceholder: "Search campaigns… (e.g. orphans, water, patients)", search: "Search", all: "All",
  sortBy: "Sort", sortRelevance: "Best match", sortPopular: "Most popular", sortProgress: "Closest to goal", sortNewest: "Newest",
  onlyZakat: "Zakat-eligible", onlyNearly: "Almost funded", results: "{n} campaigns", noResults: "No matching campaigns.", loadMore: "Load more",
  noStudy: "To take part, please use the study link the researcher sent you.", studyDraft: "This study hasn't started yet.",
  studyClosed: "This study has ended and is no longer accepting participants. Thank you for your interest.",
  previewMode: "Preview mode", previewNote: "You're trying the study as a participant. Nothing here is counted as study data.",
  previewRestart: "Start over", previewExit: "Exit preview",
  thanks: "Thank you for taking part", thanksBody: "Your answers are recorded. Your contribution helps us build better recommendation systems for charity platforms.",
  codeLine: "Your participation code", codeHint: "Keep it if you may later want your data deleted.",
  virtual: "virtual SAR",
};

export const DICT = { ar, en };
export type Key = keyof typeof ar;

export function translate(lang: Lang, key: Key, vars: Record<string, string | number> = {}) {
  let s: string = DICT[lang][key] ?? DICT.ar[key];
  for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s;
}

/** Pick the right-language field of a campaign-like object. */
export function pick<T extends Record<string, unknown>>(lang: Lang, obj: T, ar: keyof T, en: keyof T): string {
  const v = lang === "en" ? (obj[en] || obj[ar]) : obj[ar];
  return (v ?? "") as string;
}
