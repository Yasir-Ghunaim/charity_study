"""Nudge engine: decide *whether* to prompt a donor right now, and with what.

Rules produce the trigger and the evidence; the message is templated so it is
reviewable, with the agent available to rewrite it when a key is configured.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ..db import connect
from ..rec.store import get_store
from ..rec.strategies import hybrid
from ..seed.generate import in_last_ten, in_ramadan

NOW = datetime(2026, 9, 24)


def plan(user_id: str, now: datetime = NOW) -> dict:
    conn = connect()
    rows = conn.execute(
        """SELECT d.*, c.title_ar, c.category_id FROM donations d
           JOIN campaigns c ON c.id=d.campaign_id
           WHERE d.user_id=? ORDER BY d.created_at DESC""", (user_id,)).fetchall()
    conn.close()
    if not rows:
        return {"shouldNudge": False, "reason": "no_history"}

    last = datetime.fromisoformat(rows[0]["created_at"])
    days_since = (now - last).days
    gaps = []
    for a, b in zip(rows, rows[1:]):
        gaps.append((datetime.fromisoformat(a["created_at"])
                     - datetime.fromisoformat(b["created_at"])).days)
    typical = sorted(gaps)[len(gaps) // 2] if gaps else 30

    triggers = []
    if in_last_ten(now):
        triggers.append(("ramadan_last_ten", 1.0, "العشر الأواخر من رمضان"))
    elif in_ramadan(now):
        triggers.append(("ramadan", 0.85, "شهر رمضان"))
    if days_since > typical * 2 and days_since > 21:
        triggers.append(("lapsing", 0.75,
                         f"مضى {days_since} يوماً على آخر تبرع (المعتاد كل {typical} يوماً)"))
    if now.weekday() == 4:
        triggers.append(("friday", 0.35, "يوم الجمعة"))

    store = get_store()
    recs = hybrid(store, user_id=user_id, k=3, now=now)
    for r in recs:
        c = store.campaigns[r.campaign_id]
        pct = c["raised_amount"] / c["goal_amount"] if c["goal_amount"] else 0
        if pct >= 0.93:
            triggers.append(("near_complete", 0.8,
                             f"«{c['title_ar']}» تحتاج {round(100 - pct * 100)}% لإغلاقها"))
            break

    if not triggers:
        return {"shouldNudge": False, "reason": "no_trigger",
                "daysSinceLastGift": days_since, "typicalGapDays": typical}

    triggers.sort(key=lambda t: -t[1])
    code, conf, evidence = triggers[0]
    top = recs[0] if recs else None
    c = store.campaigns[top.campaign_id] if top else None

    templates = {
        "ramadan_last_ten": "في العشر الأواخر… ليلة القدر خير من ألف شهر. {title} بانتظار دعمك.",
        "ramadan": "رمضان مبارك. ضاعف أجرك بدعم {title}.",
        "lapsing": "اشتقنا لعطائك. {title} من الفرص القريبة من اهتمامك.",
        "friday": "جمعة مباركة — صدقة اليوم لها أجر خاص. {title}",
        "near_complete": "{title} على وشك الاكتمال، وتبرعك قد يكون السبب في إغلاقها.",
    }
    title = f"«{c['title_ar']}»" if c else "فرص اليوم"
    return {
        "shouldNudge": True, "trigger": code, "confidence": round(conf, 2),
        "evidenceAr": evidence,
        "channel": "push" if conf >= 0.75 else "in_app",
        "messageAr": templates[code].format(title=title),
        "campaignId": top.campaign_id if top else None,
        "campaignTitleAr": c["title_ar"] if c else None,
        "daysSinceLastGift": days_since, "typicalGapDays": typical,
        "allTriggers": [{"code": t[0], "confidence": t[1], "evidenceAr": t[2]} for t in triggers],
    }
