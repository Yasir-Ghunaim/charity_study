"""Donor profiles and giving history."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from fastapi import APIRouter, HTTPException

from ..db import connect
from ..seed.generate import ARCHETYPES

router = APIRouter()


@router.get("/users")
def list_users(limit: int = 12):
    """Demo personas — one well-populated donor per archetype, for the switcher."""
    conn = connect()
    rows = conn.execute("""
        SELECT u.id, u.name_ar, u.city, u.segment, COUNT(d.id) n, COALESCE(SUM(d.amount),0) total
        FROM users u LEFT JOIN donations d ON d.user_id = u.id
        GROUP BY u.id HAVING n >= 4 ORDER BY u.segment, n DESC""").fetchall()
    conn.close()
    best: dict[str, dict] = {}
    for r in rows:
        if r["segment"] not in best:
            best[r["segment"]] = {
                "id": r["id"], "nameAr": r["name_ar"], "city": r["city"],
                "segment": r["segment"],
                "segmentLabelAr": ARCHETYPES[r["segment"]]["label_ar"],
                "donationCount": r["n"], "totalGiven": round(r["total"]),
            }
    return list(best.values())[:limit]


@router.get("/users/{user_id}")
def profile(user_id: str):
    conn = connect()
    u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not u:
        conn.close(); raise HTTPException(404, "user not found")
    rows = conn.execute("""
        SELECT d.*, c.title_ar, c.category_id, cat.name_ar cat_ar
        FROM donations d JOIN campaigns c ON c.id=d.campaign_id
        JOIN categories cat ON cat.id=c.category_id
        WHERE d.user_id=? ORDER BY d.created_at DESC""", (user_id,)).fetchall()
    conn.close()

    cats = Counter(r["cat_ar"] for r in rows)
    kinds = Counter(r["kind"] for r in rows)
    total = sum(r["amount"] for r in rows)
    return {
        "id": u["id"], "nameAr": u["name_ar"], "city": u["city"],
        "segment": u["segment"], "segmentLabelAr": ARCHETYPES[u["segment"]]["label_ar"],
        "createdAt": u["created_at"],
        "stats": {
            "donationCount": len(rows),
            "totalGiven": round(total),
            "avgGift": round(total / len(rows)) if rows else 0,
            "categoriesSupported": len(cats),
            "topCategories": [{"nameAr": k, "count": v} for k, v in cats.most_common(4)],
            "byKind": dict(kinds),
            "hasRecurring": any(r["is_recurring"] for r in rows),
            "lastGiftAt": rows[0]["created_at"] if rows else None,
        },
        "donations": [{
            "id": r["id"], "campaignId": r["campaign_id"], "titleAr": r["title_ar"],
            "categoryAr": r["cat_ar"], "amount": r["amount"], "kind": r["kind"],
            "isRecurring": bool(r["is_recurring"]), "createdAt": r["created_at"],
        } for r in rows[:50]],
    }
