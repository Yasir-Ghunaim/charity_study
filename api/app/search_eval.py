"""Search relevance check: `python -m app.search_eval`. Hit@3 = a wanted campaign in the top 3."""
from .search import rank

# any orphan campaign is a correct answer to a bare "orphans" query
ORPHANS = ["orphan-sponsorship-monthly", "orphan-eid-clothing", "orphan-housing-furnish", "orphan-education-fund", "orphan-psych-support", "orphan-summer-club", "waqf-orphans"]

CASES = [
    ("أيتام", ORPHANS),
    ("ايتام", ORPHANS),
    ("كفالة يتيم", ["orphan-sponsorship-monthly"]),
    ("كبار السن", ["elderly-care"]),
    ("مياه", ["water-wells", "waqf-water", "mosque-water-coolers"]),
    ("عطشى", ["water-wells", "waqf-water"]),
    ("مرضى الكلى", ["dialysis-machines"]),
    ("مرضى السرطان", ["cancer-treatment-support"]),
    ("مساجد", ["mosque-maintenance", "mosque-construction", "waqf-mosques"]),
    ("أبغى أساعد ناس ما عندهم بيت", ["build-family-home", "rent-support", "home-maintenance"]),
    ("صدقة عن أمي المتوفاة", ["sadaqah-jariyah", "waqf-water", "waqf-quran", "water-wells"]),
    ("الناس اللي تضرروا من المطر", ["flood-response"]),
    ("أطفال لا يسمعون", ["hearing-aids"]),
    ("شخص على كرسي متحرك", ["wheelchairs", "accessible-home-mod"]),
    ("إفطار في رمضان", ["iftar-saem", "ramadan-food-basket"]),
    ("أضحية", ["udhiyah-sacrifice"]),
    ("ناس مسجونين بسبب الديون", ["debt-relief-gharimin"]),
    ("شنط مدرسية", ["school-bags-students"]),
    ("زراعة أشجار", ["plant-trees-desert"]),
    ("مكيفات للفقراء في الصيف", ["cooling-units-summer"]),
]


def run(verbose: bool = True) -> float:
    from .db import connect
    titles = dict(connect().execute("SELECT id, title_ar FROM campaigns").fetchall())
    hits = 0
    for q, want in CASES:
        got = [c for c, _ in rank(q, limit=5)]
        ok = any(w in got[:3] for w in want)
        hits += ok
        if verbose:
            print(("✓" if ok else "✗"), f"{q:30s}", " | ".join(titles[c] for c in got[:3]))
    score = hits / len(CASES)
    print(f"\nhit@3 = {hits}/{len(CASES)} ({score:.0%})")
    return score


if __name__ == "__main__":
    run()
