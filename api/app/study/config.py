"""Study protocol: consent text, wallet, limits, survey instruments.

Everything a participant is shown that matters for the protocol lives here,
versioned, so each record can be traced to the exact consent and questions.
Fill in the RESEARCHER_* placeholders before recruiting.
"""
import os

CONSENT_VERSION = "2026-09-v2"      # the effective version adds the study's interface, e.g. 2026-09-v2-browse
SURVEY_VERSION = "2026-09-v2"

# Interfaces a study can use. Each participant record keeps its study's mode.
MODES = {
    "assistant":        {"ar": "المساعد الذكي فقط", "en": "Assistant only", "assistant": True, "browse": False},
    "assistant_browse": {"ar": "المساعد الذكي وواجهة التصفح", "en": "Assistant + browse interface", "assistant": True, "browse": True},
    "browse":           {"ar": "واجهة التصفح فقط", "en": "Browse interface only", "assistant": False, "browse": True},
}
DEFAULT_WALLET = 1000
DEFAULT_MAX_TURNS = 25

RESEARCHER_AR = os.environ.get("STUDY_CONTACT_AR", "[اسم الباحث والجهة وبريد التواصل]")
RESEARCHER_EN = os.environ.get("STUDY_CONTACT_EN", "[Researcher name, institution and contact email]")

_DO = {
    "assistant": ("ستجيب عن أسئلة قصيرة، ثم تحصل على رصيد افتراضي قدره {wallet} ريال افتراضي توزعه على الفرص الخيرية التي تختارها، مستعيناً بمساعد ذكي. ثم تجيب عن أسئلة ختامية. تستغرق المشاركة نحو 10 إلى 15 دقيقة.",
                  "You will answer a few short questions, then receive a virtual balance of {wallet} virtual riyals to allocate to the charity campaigns you choose, with help from an AI assistant. Then you will answer some closing questions. It takes about 10 to 15 minutes."),
    "assistant_browse": ("ستجيب عن أسئلة قصيرة، ثم تحصل على رصيد افتراضي قدره {wallet} ريال افتراضي توزعه على الفرص الخيرية التي تختارها، بتصفّح الفرص بنفسك أو بالاستعانة بمساعد ذكي. ثم تجيب عن أسئلة ختامية. تستغرق المشاركة نحو 10 إلى 15 دقيقة.",
                         "You will answer a few short questions, then receive a virtual balance of {wallet} virtual riyals to allocate to the charity campaigns you choose, by browsing campaigns yourself or with help from an AI assistant. Then you will answer some closing questions. It takes about 10 to 15 minutes."),
    "browse": ("ستجيب عن أسئلة قصيرة، ثم تحصل على رصيد افتراضي قدره {wallet} ريال افتراضي توزعه على الفرص الخيرية التي تختارها بعد تصفّحها. ثم تجيب عن أسئلة ختامية. تستغرق المشاركة نحو 10 إلى 15 دقيقة.",
               "You will answer a few short questions, then receive a virtual balance of {wallet} virtual riyals to allocate to the charity campaigns you choose after browsing them. Then you will answer some closing questions. It takes about 10 to 15 minutes."),
}


def consent_for(mode: str, wallet: float) -> dict:
    """Consent text for one study. Only studies with the assistant describe it."""
    has_ai = MODES[mode]["assistant"]
    w = f"{wallet:,.0f}"
    data_ar = "اسمك المستعار، وإجاباتك عن الأسئلة، وتفاعلك مع الموقع (ما تتصفحه وتختاره وكيف توزع الرصيد)" + ("، ورسائلك إلى المساعد الذكي" if has_ai else "") + ". لا نطلب اسمك الحقيقي أو بريدك أو رقم هاتفك."
    data_en = "Your nickname, your survey answers, and your interactions with the site (what you browse, choose and how you allocate your balance)" + (", and your messages to the AI assistant" if has_ai else "") + ". We do not ask for your real name, email or phone number."
    ar = [("عن الدراسة", "تهدف هذه الدراسة إلى فهم كيف يختار الناس الفرص الخيرية، للمساعدة في تصميم أنظمة توصية أفضل لمنصات التبرع."),
          ("ماذا ستفعل", _DO[mode][0].replace("{wallet}", w)),
          ("المال افتراضي", "الرصيد افتراضي بالكامل: لا تُدفع ولا تُحوَّل أي أموال حقيقية. الفرص والجهات المعروضة نماذج تجريبية لأغراض البحث."),
          ("البيانات التي نجمعها", data_ar)]
    en = [("About the study", "This study aims to understand how people choose charity campaigns, to help design better recommendation systems for donation platforms."),
          ("What you will do", _DO[mode][1].replace("{wallet}", w)),
          ("The money is virtual", "The balance is entirely virtual: no real money is paid or transferred. The campaigns and charities shown are mock-ups created for this research."),
          ("Data we collect", data_en)]
    if has_ai:
        ar.append(("المساعد الذكي", "تُعالَج رسائلك إلى المساعد بواسطة نموذج ذكاء اصطناعي يقدّمه طرف خارجي. لا تكتب في المحادثة أي معلومات شخصية تدل على هويتك."))
        en.append(("The AI assistant", "Your messages to the assistant are processed by an AI model provided by a third party. Please do not type any personal information that could identify you."))
    ar += [("مشاركتك طوعية", "يمكنك التوقف في أي وقت دون أي تبعات. وإن أردت حذف بياناتك لاحقاً، تواصل مع الباحث مع ذكر رمز المشاركة الذي سيظهر لك."),
           ("استخدام البيانات", "تُحفظ البيانات بأمان وتُستخدم لأغراض البحث فقط، وتُعرض النتائج مجمّعة دون ما يدل على أي مشارك."),
           ("للتواصل", RESEARCHER_AR)]
    en += [("Participation is voluntary", "You can stop at any time without any consequences. If you later want your data deleted, contact the researcher with the participation code you will be shown."),
           ("How data is used", "Data is stored securely and used for research only. Results are reported in aggregate, without anything that identifies a participant."),
           ("Contact", RESEARCHER_EN)]
    return {
        "version": f"{CONSENT_VERSION}-{mode}",
        "ar": {"title": "دراسة بحثية: كيف نختار الفرص الخيرية؟", "checks": ["عمري 18 عاماً أو أكثر.", "قرأت المعلومات أعلاه وأوافق على المشاركة في هذه الدراسة."],
               "sections": [{"heading": h, "body": b} for h, b in ar]},
        "en": {"title": "Research study: how do people choose charity campaigns?", "checks": ["I am 18 years of age or older.", "I have read the information above and agree to take part in this study."],
               "sections": [{"heading": h, "body": b} for h, b in en]},
    }


# ---------------------------------------------------------------- surveys
def _o(value, ar, en):
    return {"value": value, "ar": ar, "en": en}


LIKERT = [_o(1, "لا أوافق بشدة", "Strongly disagree"), _o(2, "لا أوافق", "Disagree"),
          _o(3, "محايد", "Neutral"), _o(4, "أوافق", "Agree"), _o(5, "أوافق بشدة", "Strongly agree")]

CAUSES = [_o("orphans", "الأيتام", "Orphans"), _o("education", "التعليم", "Education"),
          _o("health", "الصحة", "Health"), _o("housing", "الإسكان", "Housing"),
          _o("mosques", "المساجد", "Mosques"), _o("relief", "الإغاثة", "Relief"),
          _o("disability", "ذوو الإعاقة", "People with disabilities"), _o("environment", "البيئة", "Environment"),
          _o("family", "الأسرة والمجتمع", "Family & community"), _o("seasonal", "المواسم (رمضان، الأضاحي…)", "Seasonal (Ramadan, Eid…)"),
          _o("waqf", "الوقف", "Endowment (waqf)")]

SURVEYS = {
    "pre": [
        {"id": "age", "type": "single", "required": True, "ar": "الفئة العمرية", "en": "Age group",
         "options": [_o("18-24", "18–24", "18–24"), _o("25-34", "25–34", "25–34"), _o("35-44", "35–44", "35–44"),
                     _o("45-54", "45–54", "45–54"), _o("55+", "55 فأكثر", "55+")]},
        {"id": "gender", "type": "single", "required": True, "ar": "الجنس", "en": "Gender",
         "options": [_o("male", "ذكر", "Male"), _o("female", "أنثى", "Female"), _o("na", "أفضّل عدم الإجابة", "Prefer not to say")]},
        {"id": "residence", "type": "single", "required": True, "ar": "مكان الإقامة", "en": "Where do you live?",
         "options": [_o("central", "المنطقة الوسطى", "Central region"), _o("western", "المنطقة الغربية", "Western region"),
                     _o("eastern", "المنطقة الشرقية", "Eastern region"), _o("southern", "المنطقة الجنوبية", "Southern region"),
                     _o("northern", "المنطقة الشمالية", "Northern region"), _o("outside", "خارج المملكة", "Outside Saudi Arabia")]},
        {"id": "give_freq", "type": "single", "required": True, "ar": "كم مرة تتبرع عادةً؟", "en": "How often do you usually donate?",
         "options": [_o("never", "لا أتبرع تقريباً", "Rarely or never"), _o("yearly", "مرات قليلة في السنة", "A few times a year"),
                     _o("monthly", "شهرياً تقريباً", "About monthly"), _o("weekly", "أسبوعياً أو أكثر", "Weekly or more")]},
        {"id": "give_types", "type": "multi", "required": False, "ar": "ما أنواع العطاء التي تمارسها؟ (اختر كل ما ينطبق)",
         "en": "Which kinds of giving do you practise? (select all that apply)",
         "options": [_o("zakat_maal", "زكاة المال", "Zakat al-maal"), _o("zakat_fitr", "زكاة الفطر", "Zakat al-fitr"),
                     _o("sadaqah", "الصدقة", "Sadaqah"), _o("waqf", "الوقف", "Waqf (endowment)"),
                     _o("kafala", "الكفالة (يتيم، أسرة…)", "Sponsorship (orphan, family…)"), _o("none", "لا شيء مما سبق", "None of these")]},
        {"id": "causes", "type": "multi", "required": False, "ar": "ما المجالات التي تدعمها عادةً؟ (اختر كل ما ينطبق)",
         "en": "Which causes do you usually support? (select all that apply)", "options": CAUSES},
        {"id": "online_platforms", "type": "single", "required": True, "ar": "هل تستخدم منصات التبرع الإلكترونية؟",
         "en": "Do you use online donation platforms?",
         "options": [_o("never", "لم أستخدمها", "Never"), _o("sometimes", "أحياناً", "Sometimes"), _o("often", "كثيراً", "Often")]},
        {"id": "choice_factors", "type": "multi", "required": False,
         "ar": "ما الذي يؤثر في اختيارك للفرصة الخيرية؟ (اختر كل ما ينطبق)",
         "en": "What influences which campaign you choose? (select all that apply)",
         "options": [_o("trust", "الثقة في الجهة المنفذة", "Trust in the charity"), _o("urgency", "الحاجة العاجلة", "Urgency of the need"),
                     _o("impact", "وضوح الأثر", "Clear impact"), _o("personal", "ارتباط شخصي بالقضية", "Personal connection to the cause"),
                     _o("religious", "الأجر والثواب", "Religious reward"), _o("recommendation", "توصية الأهل والأصدقاء", "Recommendation from family or friends"),
                     _o("near_complete", "قرب اكتمال الفرصة", "Campaign close to its goal"), _o("local", "قرب المستفيدين مني", "Beneficiaries near me")]},
    ],
}


def _l(qid, ar, en, **extra):
    return {"id": qid, "type": "likert", "required": True, "options": LIKERT, "ar": ar, "en": en, **extra}


_REAL_MONEY = {"id": "real_money", "type": "single", "required": True,
               "ar": "لو كان المال حقيقياً، هل كانت اختياراتك ستختلف؟", "en": "If the money were real, would your choices have been different?",
               "options": [_o("same", "ستكون نفسها تقريباً", "About the same"), _o("somewhat", "ستختلف قليلاً", "Somewhat different"),
                           _o("very", "ستختلف كثيراً", "Very different")]}
_WHY = {"id": "why_chosen", "type": "text", "required": False,
        "ar": "لماذا اخترت الفرص التي اخترتها؟", "en": "Why did you choose the campaigns you chose?"}


def post_questions(mode: str) -> list[dict]:
    """Same question id = same construct across studies; wording follows the interface."""
    ai = MODES[mode]["assistant"]
    tool_ar, tool_en = ("المساعد", "the assistant") if ai else ("الموقع", "the site")
    q = [
        _l("q_helped_find", f"ساعدني {tool_ar} في الوصول إلى فرص تهمّني.", f"{tool_en.capitalize()} helped me find campaigns I care about."),
        _l("q_trust_info", f"وثقت في المعلومات التي قدّمها {tool_ar}.", f"I trusted the information {tool_en} gave me."),
    ]
    if ai:
        q += [_l("q_relevant", "كانت اقتراحات المساعد مناسبة لما طلبته.", "The assistant's suggestions matched what I asked for."),
              _l("q_explanations", "ساعدتني المقارنات والشروحات على اتخاذ القرار.", "The comparisons and explanations helped me decide.")]
    if MODES[mode]["browse"]:
        q += [_l("q_info_enough", "كانت المعلومات المعروضة عن كل فرصة كافية لاتخاذ القرار.", "The information shown about each campaign was enough to decide."),
              _l("q_easy_compare", "كان من السهل المقارنة بين الفرص.", "It was easy to compare campaigns.")]
    q += [
        _l("q_control", "شعرت أن القرار النهائي كان بيدي.", "I felt the final decision was mine."),
        _l("q_pressure", "شعرت بضغط لاختيار فرص معيّنة.", "I felt pressured to choose particular campaigns."),
        _l("q_confident", "أنا واثق من اختياراتي.", "I am confident in my choices."),
        _l("q_would_use", f"سأستخدم {'مساعداً كهذا' if ai else 'موقعاً كهذا'} لو توفر في منصة تبرع حقيقية.",
           f"I would use {'an assistant' if ai else 'a site'} like this on a real donation platform."),
    ]
    if mode == "assistant_browse":
        q.append({"id": "relied_on", "type": "single", "required": True,
                  "ar": "على أيّهما اعتمدت أكثر في اختياراتك؟", "en": "Which did you rely on more for your choices?",
                  "options": [_o("assistant", "المساعد الذكي", "The assistant"), _o("browse", "تصفّح الفرص بنفسي", "Browsing myself"),
                              _o("both", "كليهما بالتساوي", "Both equally")]})
    q += [_REAL_MONEY, _WHY,
          {"id": "improve", "type": "text", "required": False,
           "ar": f"ما الذي كان سيجعل {tool_ar} أكثر فائدة لك؟", "en": f"What would have made {tool_en} more useful to you?"}]
    return q


def survey_for(phase: str, mode: str) -> list[dict]:
    return SURVEYS["pre"] if phase == "pre" else post_questions(mode)


def all_question_ids() -> list[str]:
    """Stable column order for the survey export, covering every study design."""
    ids = [q["id"] for q in SURVEYS["pre"]]
    for m in MODES:
        ids += [q["id"] for q in post_questions(m) if q["id"] not in ids]
    return ids
