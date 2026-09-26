"""Campaign catalogue, categories, cart and checkout."""
from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import CAMPAIGN_SELECT, connect, row_to_campaign
from ..rec.store import get_store

router = APIRouter()
NOW = datetime(2026, 9, 24)


@router.get("/categories")
def categories():
    conn = connect()
    rows = conn.execute("""
        SELECT cat.*, COUNT(c.id) AS campaign_count
        FROM categories cat LEFT JOIN campaigns c ON c.category_id = cat.id
        GROUP BY cat.id ORDER BY cat.sort""").fetchall()
    conn.close()
    return [{"id": r["id"], "nameAr": r["name_ar"], "nameEn": r["name_en"],
             "glyph": r["glyph"], "hue": r["hue"], "campaignCount": r["campaign_count"]}
            for r in rows]


@router.get("/campaigns")
def campaigns(
    category: str | None = None,
    q: str | None = None,
    zakat: bool | None = None,
    waqf: bool | None = None,
    featured: bool | None = None,
    near_complete: bool | None = None,
    sort: str = Query("popular", pattern="^(popular|newest|ending|progress|amount)$"),
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    where, args = ["c.status = 'active'"], []
    if category:
        where.append("c.category_id = ?"); args.append(category)
    if zakat:
        where.append("c.is_zakat = 1")
    if waqf:
        where.append("c.is_waqf = 1")
    if featured:
        where.append("c.featured = 1")
    if near_complete:
        where.append("c.raised_amount / c.goal_amount >= 0.9")

    order = {
        "newest": "c.created_at DESC",
        "ending": "c.ends_at ASC",
        "progress": "(c.raised_amount / c.goal_amount) DESC",
        "amount": "c.goal_amount DESC",
        "popular": "c.featured DESC, c.raised_amount DESC",
    }[sort]

    conn = connect()
    if q and q.strip():
        # text search: relevance order from the Arabic-aware hybrid search
        from ..search import rank
        rows = {r["id"]: r for r in conn.execute(f"{CAMPAIGN_SELECT} WHERE {' AND '.join(where)}", args)}
        conn.close()
        hits = [cid for cid, _ in rank(q, list(rows), limit=len(rows))]
        return {"total": len(hits), "items": [row_to_campaign(rows[i]) for i in hits[offset:offset + limit]]}

    sql = f"{CAMPAIGN_SELECT} WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?"
    rows = conn.execute(sql, (*args, limit, offset)).fetchall()
    total = conn.execute(
        f"SELECT COUNT(*) FROM campaigns c WHERE {' AND '.join(where)}", args).fetchone()[0]
    conn.close()
    return {"total": total, "items": [row_to_campaign(r) for r in rows]}


@router.get("/campaigns/{campaign_id}")
def campaign(campaign_id: str):
    conn = connect()
    r = conn.execute(CAMPAIGN_SELECT + " WHERE c.id = ?", (campaign_id,)).fetchone()
    if not r:
        conn.close()
        raise HTTPException(404, "campaign not found")
    out = row_to_campaign(r)
    agg = conn.execute(
        "SELECT COUNT(*) n, COUNT(DISTINCT user_id) d FROM donations WHERE campaign_id=?",
        (campaign_id,)).fetchone()
    out["donationCount"] = agg["n"]
    out["donorCount"] = agg["d"]
    out["updates"] = [{"textAr": u["text_ar"], "textEn": u["text_en"], "createdAt": u["created_at"]} for u in conn.execute(
        "SELECT text_ar, text_en, created_at FROM campaign_updates WHERE campaign_id=? ORDER BY created_at DESC LIMIT 4",
        (campaign_id,))]
    ch = conn.execute("SELECT governance_score, overhead_pct, audited_year, founded_year FROM charities WHERE id=?",
                      (r["charity_id"],)).fetchone()
    out["charityProfile"] = ({"governanceScore": ch["governance_score"], "overheadPct": ch["overhead_pct"],
                              "auditedYear": ch["audited_year"], "foundedYear": ch["founded_year"]} if ch else None)
    conn.close()
    return out


class EventIn(BaseModel):
    userId: str
    campaignId: str | None = None
    type: str
    sessionId: str | None = None
    meta: dict | None = None


@router.post("/events")
def log_event(e: EventIn):
    conn = connect()
    conn.execute(
        "INSERT INTO events (user_id,campaign_id,type,session_id,meta,created_at) VALUES (?,?,?,?,?,?)",
        (e.userId, e.campaignId, e.type, e.sessionId,
         json.dumps(e.meta, ensure_ascii=False) if e.meta else None, datetime.now().isoformat()))
    conn.commit(); conn.close()
    return {"ok": True}


# ------------------------------------------------------------------- cart
class CartIn(BaseModel):
    userId: str
    campaignId: str
    amount: float


@router.get("/cart/{user_id}")
def get_cart(user_id: str):
    conn = connect()
    rows = conn.execute(
        CAMPAIGN_SELECT.replace("SELECT c.*", "SELECT c.*, ci.amount AS cart_amount") +
        " JOIN cart_items ci ON ci.campaign_id = c.id WHERE ci.user_id = ? ORDER BY ci.created_at",
        (user_id,)).fetchall()
    conn.close()
    items = []
    for r in rows:
        c = row_to_campaign(r)
        c["cartAmount"] = r["cart_amount"]
        items.append(c)
    return {"items": items, "total": sum(i["cartAmount"] for i in items)}


@router.post("/cart")
def add_cart(c: CartIn):
    conn = connect()
    conn.execute(
        """INSERT INTO cart_items (user_id,campaign_id,amount,created_at) VALUES (?,?,?,?)
           ON CONFLICT(user_id,campaign_id) DO UPDATE SET amount=excluded.amount""",
        (c.userId, c.campaignId, c.amount, datetime.now().isoformat()))
    conn.execute(
        "INSERT INTO events (user_id,campaign_id,type,created_at) VALUES (?,?,'add_to_cart',?)",
        (c.userId, c.campaignId, datetime.now().isoformat()))
    conn.commit(); conn.close()
    return {"ok": True}


@router.delete("/cart/{user_id}/{campaign_id}")
def del_cart(user_id: str, campaign_id: str):
    conn = connect()
    conn.execute("DELETE FROM cart_items WHERE user_id=? AND campaign_id=?", (user_id, campaign_id))
    conn.commit(); conn.close()
    return {"ok": True}


# --------------------------------------------------------------- checkout
class DonateIn(BaseModel):
    userId: str
    campaignId: str | None = None
    amount: float | None = None
    kind: str = "sadaqah"
    isRecurring: bool = False
    source: str = "feed"
    fromCart: bool = False


@router.post("/donations")
def donate(d: DonateIn):
    conn = connect()
    now = datetime.now().isoformat()
    made = []

    if d.fromCart:
        rows = conn.execute("SELECT campaign_id, amount FROM cart_items WHERE user_id=?",
                            (d.userId,)).fetchall()
        if not rows:
            conn.close(); raise HTTPException(400, "cart is empty")
        pairs = [(r["campaign_id"], r["amount"]) for r in rows]
        conn.execute("DELETE FROM cart_items WHERE user_id=?", (d.userId,))
    else:
        if not d.campaignId or not d.amount:
            conn.close(); raise HTTPException(400, "campaignId and amount are required")
        pairs = [(d.campaignId, d.amount)]

    for cid, amt in pairs:
        did = f"d{uuid.uuid4().hex[:10]}"
        conn.execute(
            """INSERT INTO donations (id,user_id,campaign_id,amount,kind,is_recurring,source,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (did, d.userId, cid, amt, d.kind, int(d.isRecurring), d.source, now))
        conn.execute("UPDATE campaigns SET raised_amount = raised_amount + ? WHERE id = ?", (amt, cid))
        conn.execute(
            "INSERT INTO events (user_id,campaign_id,type,created_at) VALUES (?,?,'donate',?)",
            (d.userId, cid, now))
        made.append({"id": did, "campaignId": cid, "amount": amt})

    conn.commit(); conn.close()
    get_store(force=True)   # small catalogue: refresh so the next rec reflects the gift
    return {"ok": True, "donations": made, "total": sum(a for _, a in pairs)}
