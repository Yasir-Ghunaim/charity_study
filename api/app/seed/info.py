"""Information the agent fetches on the donor's behalf.

All of it is invented for the prototype. Charity names are fictional on
purpose: governance scores and licence numbers must not be attached to real
organisations.
"""

# id, name_ar, founded, hq, focus categories, one-line description
CHARITIES = [
    ("athar",   "جمعية الأثر الخيرية",          2004, "الرياض",          ["general", "family", "relief"],
     "جمعية عامة تنفذ برامج الإعاشة والدعم الأسري في عدة مناطق."),
    ("rifd",    "جمعية رِفد لرعاية الأيتام",     2009, "مكة المكرمة",     ["orphans"],
     "متخصصة في كفالة الأيتام ورعايتهم تعليمياً ونفسياً حتى سن الاستقلال."),
    ("suqya",   "مؤسسة سُقيا الوقفية",           2012, "المدينة المنورة", ["waqf", "relief", "mosques"],
     "مؤسسة وقفية تدير أصولاً يُصرف ريعها على السقيا وعمارة المساجد."),
    ("namaa",   "جمعية نماء للتنمية الأسرية",    2011, "المنطقة الشرقية", ["family", "housing"],
     "تعمل على تمكين الأسر اقتصادياً وحل مشكلات السكن والديون."),
    ("shifa",   "جمعية شفاء لدعم المرضى",        2007, "الرياض",          ["health"],
     "تغطي تكاليف العلاج والنقل الطبي للمرضى غير المقتدرين."),
    ("buyut",   "جمعية بيوت الخير للإسكان",      2015, "القصيم",          ["housing"],
     "تبني وترمم مساكن الأسر المحتاجة وتؤثثها."),
    ("amal",    "جمعية أمل لذوي الإعاقة",        2010, "عسير",            ["disability"],
     "تقدم الأجهزة التعويضية والتأهيل والتوظيف لذوي الإعاقة."),
    ("ghiras",  "جمعية غراس البيئية",            2019, "تبوك",            ["environment"],
     "جمعية بيئية ناشئة تعمل في التشجير وحفظ النعمة والطاقة النظيفة."),
    ("manara",  "جمعية منارة لتعليم القرآن",     1998, "المدينة المنورة", ["mosques", "education"],
     "تشرف على حلقات التحفيظ وطباعة المصاحف ودعم الأئمة."),
    ("awn",     "جمعية عون للإغاثة",             2013, "جازان",           ["relief", "seasonal"],
     "استجابة سريعة للكوارث وبرامج موسمية في رمضان والشتاء."),
    ("midad",   "جمعية مِداد التعليمية",         2016, "حائل",            ["education"],
     "تدعم الطلاب المحتاجين بالرسوم والأجهزة والتدريب المهني."),
    ("wafa",    "جمعية وفاء لكبار السن",         2014, "الباحة",          ["family", "health"],
     "رعاية منزلية وصحية لكبار السن الذين لا عائل لهم."),
]

# which charities plausibly run campaigns in each category
CATEGORY_CHARITIES = {
    "orphans": ["rifd", "athar"], "education": ["midad", "manara"], "health": ["shifa", "wafa"],
    "housing": ["buyut", "namaa"], "mosques": ["manara", "suqya"], "relief": ["awn", "athar"],
    "disability": ["amal"], "environment": ["ghiras"], "family": ["namaa", "wafa", "athar"],
    "seasonal": ["awn", "athar"], "general": ["athar", "awn"], "waqf": ["suqya", "manara"],
}

# slug -> (what one unit is, cost of one unit in SAR)
IMPACT_UNITS = {
    "orphan-sponsorship-monthly": ("كفالة يتيم لمدة شهر", 300),
    "orphan-eid-clothing": ("كسوة عيد ليتيم", 250),
    "orphan-housing-furnish": ("تأثيث غرفة لأسرة أيتام", 3500),
    "orphan-education-fund": ("رسوم فصل دراسي جامعي ليتيم", 6000),
    "orphan-psych-support": ("جلسة إرشاد نفسي", 200),
    "orphan-summer-club": ("اشتراك يتيم في النادي الصيفي", 450),
    "school-bags-students": ("حقيبة مدرسية مكتملة", 150),
    "tuition-support": ("رسوم فصل دراسي لطالب", 2500),
    "quran-memorization": ("مكافأة معلم تحفيظ لشهر", 2000),
    "digital-devices-students": ("جهاز لوحي مع اشتراك إنترنت لعام", 1400),
    "literacy-adults": ("مقعد في دورة محو الأمية", 600),
    "vocational-training": ("برنامج تدريب مهني لمتدرب", 4000),
    "cancer-treatment-support": ("جلسة علاج كيميائي", 3000),
    "dialysis-machines": ("جلسة غسيل كلوي", 450),
    "medical-escort": ("رحلة علاج مع السكن لمريض ومرافقه", 1800),
    "prosthetics-fund": ("طرف صناعي مع التأهيل", 12000),
    "smoking-awareness": ("حملة توعوية في مدرسة", 1500),
    "mother-child-care": ("باقة رعاية لأم ومولود", 900),
    "home-maintenance": ("ترميم منزل متوسط", 15000),
    "rent-support": ("إيجار شهر لأسرة", 1500),
    "home-appliances": ("جهاز منزلي أساسي", 1800),
    "build-family-home": ("وحدة سكنية مكتملة", 180000),
    "furniture-bank": ("تأهيل قطعة أثاث وتوصيلها", 200),
    "cooling-units-summer": ("مكيف مع التركيب", 2200),
    "mosque-construction": ("متر مربع من مسجد", 1500),
    "mosque-maintenance": ("صيانة دورية لمسجد", 5000),
    "mosque-water-coolers": ("برادة مياه مع صيانة عام", 2800),
    "mosque-carpets": ("متر مربع من الفرش", 120),
    "quran-copies": ("مصحف", 25),
    "imam-support": ("مكافأة إمام لشهر", 1500),
    "emergency-relief-fund": ("حقيبة إغاثة عاجلة لأسرة", 500),
    "flood-response": ("إيواء أسرة متضررة لأسبوع", 1200),
    "winter-blankets": ("حقيبة شتوية لأسرة", 350),
    "food-baskets": ("سلة غذائية شهرية لأسرة", 400),
    "water-wells": ("بئر مع المضخة", 35000),
    "refugee-support": ("مساعدة شهرية لأسرة نازحة", 800),
    "wheelchairs": ("كرسي متحرك يدوي", 1200),
    "hearing-aids": ("سماعة طبية", 3500),
    "autism-center": ("شهر تأهيل لطفل", 2500),
    "accessible-home-mod": ("تهيئة دورة مياه لذوي الإعاقة", 7000),
    "braille-library": ("كتاب بطريقة برايل", 180),
    "disability-employment": ("برنامج تأهيل وظيفي لمستفيد", 5000),
    "plant-trees-desert": ("شجرة محلية مع الري لعام", 60),
    "beach-cleanup": ("حملة تنظيف شاطئ", 3000),
    "food-waste-reduction": ("وجبة فائضة يعاد توزيعها", 8),
    "solar-panels-villages": ("نظام طاقة شمسية لمنزل", 9000),
    "recycling-schools": ("محطة فرز في مدرسة", 2500),
    "wildlife-protection": ("رعاية كائن مهدد لشهر", 700),
    "productive-families": ("معدات مشروع أسرة منتجة", 8000),
    "marriage-support": ("مساهمة في تجهيز زواج", 10000),
    "debt-relief-gharimin": ("سداد دين غارم (متوسط)", 25000),
    "widows-support": ("دعم شهري لأرملة معيلة", 1000),
    "elderly-care": ("زيارة رعاية منزلية لمسن", 250),
    "family-counseling": ("جلسة استشارة أسرية", 300),
    "iftar-saem": ("وجبة إفطار صائم", 15),
    "zakat-alfitr": ("زكاة فطر عن فرد", 25),
    "udhiyah-sacrifice": ("أضحية", 1400),
    "ramadan-food-basket": ("سلة رمضانية لأسرة", 450),
    "hajj-pilgrim-services": ("وجبة ومياه لحاج", 30),
    "eid-gifts-children": ("هدية عيد لطفل", 100),
    "general-sadaqah": ("مساهمة عامة", 10),
    "sadaqah-jariyah": ("سهم في مشروع جارٍ", 100),
    "zakat-almaal": ("حصة زكاة لأسرة مستحقة لشهر", 1000),
    "volunteer-programs": ("تجهيز متطوع", 400),
    "community-parks": ("متر مربع من حديقة حي", 250),
    "emergency-medical-fund": ("تدخل طبي عاجل (متوسط)", 5000),
    "waqf-education": ("سهم وقفي", 1000),
    "waqf-health": ("سهم وقفي", 1000),
    "waqf-orphans": ("سهم وقفي", 1000),
    "waqf-mosques": ("سهم وقفي", 1000),
    "waqf-water": ("سهم وقفي", 1000),
    "waqf-quran": ("سهم وقفي", 500),
}

# zakat recipient category (مصرف) as classified by the executing charity
ZAKAT_CATEGORY = {"debt-relief-gharimin": "الغارمين"}
DEFAULT_ZAKAT_CATEGORY = "الفقراء والمساكين"

UPDATE_TEMPLATES = [
    "تم صرف دفعة جديدة من التبرعات وتنفيذ المرحلة {phase} من المشروع.",
    "زيارة ميدانية من فريق الجمعية في {region} للتحقق من التنفيذ.",
    "وصل عدد المستفيدين المسجلين إلى {n}.",
    "نُشر تقرير الإنجاز الربعي للمشروع ويمكن طلبه من الجمعية.",
    "تم تحديث قائمة المستحقين بعد دراسة الحالات الجديدة.",
]

GOLD_PRICE_SAR_PER_GRAM = 400.0   # approximate, set for the demo; nisab = 85 g

# Everyday words donors use for each cause (colloquial and MSA). Search indexes
# these alongside the campaign text so «بيت» finds «مسكن» and «عطش» finds «سقيا».
CATEGORY_TERMS = {
    "orphans": "يتيم أيتام يتامى طفل فقد والده كفالة",
    "education": "تعليم مدرسة مدارس طالب طلاب طالبات دراسة جامعة رسوم تعلم بنات",
    "health": "صحة مرض مرضى علاج مستشفى دواء أدوية عملية طبي",
    "housing": "بيت بيوت منزل مسكن سكن مأوى إيجار ايجار أسرة بلا مأوى ترميم عفش أثاث",
    "mosques": "مسجد مساجد جامع مصلى صلاة قرآن مصاحف",
    "relief": "إغاثة كارثة كوارث سيول مطر أمطار فيضان زلزال جوع طعام غذاء عطش ماء مياه نازحين",
    "disability": "إعاقة معاق معاقين ذوي الإعاقة كرسي متحرك أصم سمع بصر كفيف مكفوف توحد",
    "environment": "بيئة شجر أشجار تشجير زراعة تصحر نظافة تدوير طاقة",
    "family": "أسرة أسر عائلة أرامل أرملة مطلقات زواج ديون دين مسن مسنين كبار السن محتاج فقير",
    "seasonal": "رمضان إفطار صائم عيد أضحية حج عمرة موسم زكاة الفطر",
    "general": "صدقة زكاة عام خير أجر متوفى متوفاة عن والدي عن أمي",
    "waqf": "وقف أوقاف صدقة جارية دائم مستمر أجر مستمر متوفى",
}

CATEGORY_TERMS_EN = {
    "orphans": "orphan orphans child children sponsorship kafala",
    "education": "education school schools student students study university fees learning girls",
    "health": "health patient patients sick treatment hospital medicine medical",
    "housing": "house home homes housing shelter homeless rent furniture repair",
    "mosques": "mosque mosques prayer quran",
    "relief": "relief disaster flood floods rain hunger food water thirst refugees displaced",
    "disability": "disability disabled wheelchair deaf hearing blind autism",
    "environment": "environment trees planting desert clean recycling energy",
    "family": "family families widow widows marriage debt elderly poor needy",
    "seasonal": "ramadan iftar eid sacrifice hajj pilgrims season",
    "general": "charity sadaqah zakat general reward deceased mother father",
    "waqf": "waqf endowment ongoing charity lasting reward deceased",
}
