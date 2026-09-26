"""Generate the synthetic world: campaigns, donors, donation history, events.

Donors are drawn from behavioural archetypes with overlapping category
affinities and seasonal giving patterns. The archetype is stored on the user
row as `segment` and is treated as hidden ground truth: the recommenders never
read it, the evaluation harness does.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from ..db import connect, init_db
from .catalog import CAMPAIGNS, CATEGORIES, REGIONS
from . import en as en_data, info

SEED = 20260924
NOW = datetime(2026, 9, 24)
HISTORY_START = NOW - timedelta(days=365 * 3)
N_DONORS = 600

# ---------------------------------------------------------------- seasonality

RAMADAN = [
    (datetime(2023, 3, 23), datetime(2023, 4, 20)),
    (datetime(2024, 3, 11), datetime(2024, 4, 9)),
    (datetime(2025, 3, 1), datetime(2025, 3, 30)),
    (datetime(2026, 2, 18), datetime(2026, 3, 19)),
]
HAJJ = [
    (datetime(2023, 6, 18), datetime(2023, 6, 28)),
    (datetime(2024, 6, 6), datetime(2024, 6, 16)),
    (datetime(2025, 5, 27), datetime(2025, 6, 6)),
    (datetime(2026, 5, 17), datetime(2026, 5, 27)),
]


def _in(d: datetime, windows) -> bool:
    return any(a <= d <= b for a, b in windows)


def in_ramadan(d: datetime) -> bool:
    return _in(d, RAMADAN)


def in_last_ten(d: datetime) -> bool:
    return any(b - timedelta(days=10) <= d <= b for _, b in RAMADAN)


def seasonal_multiplier(d: datetime, category: str) -> float:
    """How much more likely a donation to `category` is on date `d`."""
    m = 1.0
    if in_ramadan(d):
        m *= 3.0
        if category in ("seasonal", "general", "orphans"):
            m *= 2.2
        if in_last_ten(d):
            m *= 2.0
    if _in(d, HAJJ) and category == "seasonal":
        m *= 4.0
    if d.month in (12, 1) and category == "relief":
        m *= 2.5
    if d.month in (8, 9) and category == "education":
        m *= 2.8
    if d.month in (6, 7, 8) and category == "housing":
        m *= 1.4          # cooling units
    if d.weekday() == 4:  # Friday
        m *= 1.6
    return m


# ----------------------------------------------------------------- archetypes
# category affinity weights -> the hidden structure the recommender must find
ARCHETYPES = {
    "orphan_sponsor": dict(
        label_ar="كافل أيتام",
        affinity={"orphans": 0.58, "education": 0.18, "family": 0.12, "general": 0.07, "seasonal": 0.05},
        amount=(6.0, 0.55), per_year=11, recurring=0.75, zakat_pref=0.45, waqf_pref=0.10),
    "zakat_annual": dict(
        label_ar="مزكٍّ سنوي",
        affinity={"general": 0.30, "family": 0.24, "relief": 0.18, "orphans": 0.16, "health": 0.12},
        amount=(9.2, 0.70), per_year=2.5, recurring=0.05, zakat_pref=0.95, waqf_pref=0.05),
    "micro_frequent": dict(
        label_ar="متبرع صغير متكرر",
        affinity={"general": 0.34, "seasonal": 0.22, "mosques": 0.16, "relief": 0.16, "orphans": 0.12},
        amount=(3.4, 0.60), per_year=34, recurring=0.15, zakat_pref=0.10, waqf_pref=0.10),
    "health_focused": dict(
        label_ar="داعم القطاع الصحي",
        affinity={"health": 0.62, "disability": 0.22, "general": 0.09, "family": 0.07},
        amount=(6.6, 0.65), per_year=7, recurring=0.30, zakat_pref=0.40, waqf_pref=0.15),
    "mosque_waqf": dict(
        label_ar="واقف ومُعمِّر مساجد",
        affinity={"mosques": 0.42, "waqf": 0.40, "general": 0.10, "education": 0.08},
        amount=(8.4, 0.75), per_year=4, recurring=0.20, zakat_pref=0.05, waqf_pref=0.85),
    "ramadan_seasonal": dict(
        label_ar="متبرع موسمي",
        affinity={"seasonal": 0.66, "relief": 0.16, "general": 0.10, "orphans": 0.08},
        amount=(5.6, 0.60), per_year=4, recurring=0.05, zakat_pref=0.55, waqf_pref=0.05),
    "green_youth": dict(
        label_ar="متبرع شبابي بيئي",
        affinity={"environment": 0.54, "education": 0.24, "general": 0.12, "health": 0.10},
        amount=(4.2, 0.55), per_year=9, recurring=0.20, zakat_pref=0.05, waqf_pref=0.25),
    "relief_responsive": dict(
        label_ar="مستجيب للأزمات",
        affinity={"relief": 0.62, "seasonal": 0.14, "health": 0.12, "general": 0.12},
        amount=(6.2, 0.80), per_year=6, recurring=0.05, zakat_pref=0.50, waqf_pref=0.05),
    "family_housing": dict(
        label_ar="داعم الأسر والإسكان",
        affinity={"housing": 0.40, "family": 0.38, "orphans": 0.12, "general": 0.10},
        amount=(6.8, 0.65), per_year=6, recurring=0.35, zakat_pref=0.60, waqf_pref=0.08),
    "education_patron": dict(
        label_ar="راعي التعليم",
        affinity={"education": 0.58, "orphans": 0.18, "disability": 0.12, "waqf": 0.12},
        amount=(7.4, 0.70), per_year=5, recurring=0.30, zakat_pref=0.35, waqf_pref=0.30),
    "inclusion_advocate": dict(
        label_ar="داعم ذوي الإعاقة",
        affinity={"disability": 0.60, "health": 0.20, "education": 0.12, "family": 0.08},
        amount=(6.0, 0.60), per_year=6, recurring=0.28, zakat_pref=0.40, waqf_pref=0.12),
}

ARCH_WEIGHTS = [0.14, 0.08, 0.16, 0.10, 0.09, 0.08, 0.07, 0.07, 0.09, 0.06, 0.06]

FIRST_M = ["محمد", "عبدالله", "أحمد", "خالد", "فهد", "سعود", "ناصر", "بندر", "تركي", "عمر",
           "سلطان", "ماجد", "يوسف", "إبراهيم", "طلال", "زياد", "رائد", "وليد", "مشعل", "فيصل"]
FIRST_F = ["نورة", "سارة", "هند", "لطيفة", "منيرة", "ريم", "الجوهرة", "مها", "أمل", "شهد",
           "دانة", "لمى", "غادة", "أسماء", "رغد", "بشاير", "جواهر", "عبير", "نوف", "وجدان"]
LAST = ["العتيبي", "القحطاني", "الغامدي", "الدوسري", "الشمري", "الحربي", "المطيري", "الزهراني",
        "السبيعي", "البقمي", "الشهري", "العنزي", "الرشيدي", "الخالدي", "المالكي", "العمري",
        "السهلي", "الجهني", "الأحمدي", "الصاعدي", "بن سعيد", "آل فهد"]


def rnd_name(rng: random.Random) -> str:
    first = rng.choice(FIRST_M if rng.random() < 0.55 else FIRST_F)
    return f"{first} {rng.choice(LAST)}"


def nice_amount(x: float, minimum: float) -> float:
    """Round to an amount a human would actually type."""
    x = max(minimum, x)
    if x < 100:
        return float(max(minimum, round(x / 5) * 5))
    if x < 1000:
        return float(round(x / 25) * 25)
    if x < 10000:
        return float(round(x / 100) * 100)
    return float(round(x / 500) * 500)


# ------------------------------------------------------------------ generator

def build() -> dict:
    rng = random.Random(SEED)
    conn = connect()
    init_db(conn)
    cur = conn.cursor()
    for t in ("cart_items", "events", "donations", "campaign_updates", "users",
              "campaigns", "charities", "categories"):
        cur.execute(f"DELETE FROM {t}")

    # -- categories
    for i, (cid, ar, en, glyph, hue) in enumerate(CATEGORIES):
        cur.execute(
            "INSERT INTO categories (id,name_ar,name_en,glyph,hue,sort) VALUES (?,?,?,?,?,?)",
            (cid, ar, en, glyph, hue, i))

    # -- charities (fictional). Separate RNG so enrichment never perturbs the
    #    donor simulation below.
    irng = random.Random(SEED + 1)
    charity_name = {}
    for cid, name, founded, hq, focus, desc in info.CHARITIES:
        charity_name[cid] = name
        cur.execute(
            """INSERT INTO charities (id,name_ar,license_no,founded_year,hq_region,focus,description_ar,
               name_en,description_en,governance_score,overhead_pct,audited_year,beneficiaries_last_year)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, name, f"{irng.randint(100, 4999)}", founded, hq, json.dumps(focus), desc,
             en_data.CHARITIES_EN[cid][0], en_data.CHARITIES_EN[cid][1],
             irng.randint(68, 97), round(irng.uniform(4.5, 14.0), 1),
             irng.choice([2025, 2025, 2025, 2024, None]) if founded > 2016 else irng.choice([2025, 2025, 2024]),
             irng.randint(800, 60000)))

    # -- campaigns
    popularity: dict[str, float] = {}
    campaigns: dict[str, dict] = {}
    for slug, t_ar, t_en, cat, zakat, waqf, tags, blurb in CAMPAIGNS:
        goal = nice_amount(rng.lognormvariate(12.4, 0.85), 50_000)
        goal = min(goal, 4_000_000)
        created = HISTORY_START + timedelta(days=rng.randint(0, 900))
        ends = created + timedelta(days=rng.randint(180, 540))
        min_don = rng.choice([10, 10, 25, 50, 100])
        base = [min_don * k for k in (1, 5, 10, 25)]
        pop = rng.lognormvariate(0, 0.6)
        popularity[slug] = pop
        campaigns[slug] = dict(category=cat, is_zakat=zakat, is_waqf=waqf,
                               min_donation=min_don, created=created, goal=goal)
        cur.execute(
            """INSERT INTO campaigns (id,title_ar,title_en,description_ar,description_en,
               category_id,tags,goal_amount,raised_amount,beneficiaries,region,charity,
               is_zakat,is_waqf,min_donation,suggested_amounts,created_at,ends_at,status,featured)
               VALUES (?,?,?,?,?,?,?,?,0,?,?,?,?,?,?,?,?,?,?,?)""",
            (slug, t_ar, t_en, blurb, en_data.DESCRIPTIONS_EN[slug], cat, json.dumps(tags, ensure_ascii=False), goal,
             rng.randint(40, 5000), rng.choice(REGIONS), "",
             int(zakat), int(waqf), min_don, json.dumps(base),
             created.isoformat(), ends.isoformat(), "active", int(rng.random() < 0.15)))

    for slug, _, _, cat, zakat, *_ in CAMPAIGNS:
        ch = irng.choice(info.CATEGORY_CHARITIES[cat])
        unit, cost = info.IMPACT_UNITS[slug]
        cur.execute(
            "UPDATE campaigns SET charity=?, charity_id=?, unit_ar=?, unit_en=?, unit_cost=?, zakat_category=? WHERE id=?",
            (charity_name[ch], ch, unit, en_data.UNITS_EN[slug], cost,
             info.ZAKAT_CATEGORY.get(slug, info.DEFAULT_ZAKAT_CATEGORY) if zakat else None, slug))
        region = cur.execute("SELECT region FROM campaigns WHERE id=?", (slug,)).fetchone()[0]
        created = campaigns[slug]["created"]
        for k in range(irng.randint(2, 4)):
            when = created + timedelta(days=irng.randint(15, max(16, (NOW - created).days)))
            if when > NOW:
                continue
            ti, n = irng.randrange(len(info.UPDATE_TEMPLATES)), irng.randint(20, 2000)
            text = info.UPDATE_TEMPLATES[ti].format(phase=k + 1, region=region, n=n)
            text_en = en_data.UPDATE_TEMPLATES_EN[ti].format(phase=k + 1, region=en_data.REGIONS_EN.get(region, region), n=n)
            cur.execute("INSERT INTO campaign_updates (campaign_id,text_ar,text_en,created_at) VALUES (?,?,?,?)",
                        (slug, text, text_en, when.isoformat()))

    by_cat: dict[str, list[str]] = {}
    for slug, c in campaigns.items():
        by_cat.setdefault(c["category"], []).append(slug)

    # -- donors
    arch_names = list(ARCHETYPES)
    donations, events = [], []
    for i in range(N_DONORS):
        uid = f"u{i+1:04d}"
        primary = rng.choices(arch_names, weights=ARCH_WEIGHTS)[0]
        a = ARCHETYPES[primary]
        affinity = dict(a["affinity"])
        # blend in a secondary taste so segments overlap realistically
        if rng.random() < 0.45:
            sec = rng.choice([x for x in arch_names if x != primary])
            for k, v in ARCHETYPES[sec]["affinity"].items():
                affinity[k] = affinity.get(k, 0) + v * 0.30
        # everyone has a little residual interest everywhere
        for cid, *_ in CATEGORIES:
            affinity[cid] = affinity.get(cid, 0) + 0.015
        tot = sum(affinity.values())
        affinity = {k: v / tot for k, v in affinity.items()}

        joined = HISTORY_START + timedelta(days=rng.randint(0, 900))
        cur.execute(
            "INSERT INTO users (id,name_ar,email,city,segment,language,created_at) VALUES (?,?,?,?,?,?,?)",
            (uid, rnd_name(rng), f"donor{i+1}@example.sa", rng.choice(REGIONS),
             primary, "ar", joined.isoformat()))

        years = max(0.25, (NOW - joined).days / 365)
        n = max(1, int(rng.gauss(a["per_year"] * years, a["per_year"] * years * 0.35)))
        n = min(n, 220)

        # sample candidate days, keep them in proportion to seasonal pull
        span = (NOW - joined).days or 1
        picked = []
        attempts = 0
        while len(picked) < n and attempts < n * 40:
            attempts += 1
            d = joined + timedelta(days=rng.randint(0, span),
                                   hours=rng.randint(6, 23), minutes=rng.randint(0, 59))
            cat = rng.choices(list(affinity), weights=list(affinity.values()))[0]
            pool = [s for s in by_cat[cat] if campaigns[s]["created"] <= d]
            if not pool:
                continue
            slug = rng.choices(pool, weights=[popularity[s] for s in pool])[0]
            if rng.random() > min(1.0, seasonal_multiplier(d, cat) / 6.0):
                continue
            picked.append((d, slug, cat))

        recurring_slug = None
        if rng.random() < a["recurring"] and picked:
            recurring_slug = max(set(s for _, s, _ in picked), key=lambda s: sum(1 for _, x, _ in picked if x == s))

        for d, slug, cat in sorted(picked):
            c = campaigns[slug]
            amt = nice_amount(rng.lognormvariate(*a["amount"]), c["min_donation"])
            if in_last_ten(d):
                amt = nice_amount(amt * rng.uniform(1.3, 2.2), c["min_donation"])
            kind = "sadaqah"
            if c["is_waqf"] and rng.random() < a["waqf_pref"]:
                kind = "waqf"
            elif c["is_zakat"] and rng.random() < a["zakat_pref"]:
                kind = "zakat"
                amt = nice_amount(amt * rng.uniform(1.5, 3.0), c["min_donation"])
            src = rng.choices(["feed", "category", "search", "direct"], weights=[0.45, 0.28, 0.17, 0.10])[0]
            sess = f"s{rng.randint(10**7, 10**8)}"
            donations.append((f"d{len(donations)+1:07d}", uid, slug, amt, kind,
                              int(slug == recurring_slug), src, d.isoformat()))
            # browsing that led to the gift
            events.append((uid, slug, "view", sess, None, (d - timedelta(minutes=rng.randint(2, 25))).isoformat()))
            events.append((uid, slug, "click", sess, None, (d - timedelta(minutes=rng.randint(1, 3))).isoformat()))
            events.append((uid, slug, "donate", sess, None, d.isoformat()))
            for other in rng.sample(by_cat[cat], min(len(by_cat[cat]), rng.randint(1, 3))):
                if other != slug and campaigns[other]["created"] <= d:
                    events.append((uid, other, "view", sess,
                                   None, (d - timedelta(minutes=rng.randint(3, 30))).isoformat()))
            if rng.random() < 0.18:
                events.append((uid, slug, "share", sess, None, (d + timedelta(minutes=2)).isoformat()))

        # pure browsing sessions with no gift
        for _ in range(int(n * rng.uniform(0.6, 1.8))):
            d = joined + timedelta(days=rng.randint(0, span), hours=rng.randint(7, 23))
            cat = rng.choices(list(affinity), weights=list(affinity.values()))[0]
            pool = [s for s in by_cat[cat] if campaigns[s]["created"] <= d]
            if not pool:
                continue
            sess = f"s{rng.randint(10**7, 10**8)}"
            for slug in rng.sample(pool, min(len(pool), rng.randint(1, 4))):
                events.append((uid, slug, "view", sess, None, d.isoformat()))

    cur.executemany(
        """INSERT INTO donations (id,user_id,campaign_id,amount,kind,is_recurring,source,created_at)
           VALUES (?,?,?,?,?,?,?,?)""", donations)
    cur.executemany(
        """INSERT INTO events (user_id,campaign_id,type,session_id,meta,created_at)
           VALUES (?,?,?,?,?,?)""", events)

    # -- raised amounts: simulated gifts + an "everyone else" baseline, capped
    for slug, c in campaigns.items():
        got = cur.execute("SELECT COALESCE(SUM(amount),0) FROM donations WHERE campaign_id=?",
                          (slug,)).fetchone()[0]
        target_pct = rng.choices([rng.uniform(.15, .45), rng.uniform(.45, .80),
                                  rng.uniform(.80, .96)], weights=[.30, .48, .22])[0]
        raised = min(c["goal"] * target_pct, c["goal"] * 0.985)
        raised = max(raised, min(got, c["goal"] * 0.985))
        cur.execute("UPDATE campaigns SET raised_amount=? WHERE id=?", (round(raised), slug))

    conn.commit()
    stats = dict(
        categories=cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0],
        campaigns=cur.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0],
        users=cur.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        donations=cur.execute("SELECT COUNT(*) FROM donations").fetchone()[0],
        events=cur.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        volume=round(cur.execute("SELECT SUM(amount) FROM donations").fetchone()[0]),
    )
    conn.close()
    return stats


if __name__ == "__main__":
    for k, v in build().items():
        print(f"{k:>12}: {v:,}")
