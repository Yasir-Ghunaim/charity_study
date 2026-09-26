"""Tools for the study's donation assistant.

Two families:
  * information tools fetch what a participant would otherwise dig for:
    campaign facts, the executing charity's record, what an amount achieves,
    zakat maths, their own wallet.
  * presentation tools put real UI in front of the participant: campaign
    cards, a comparison, a proposed allocation. The participant, never the
    agent, moves any virtual money.

The participant is bound server-side (ToolContext); the model never supplies
an id, so a prompt cannot read or change another participant's data.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from ..db import CAMPAIGN_SELECT, connect, row_to_campaign
from ..seed.info import GOLD_PRICE_SAR_PER_GRAM

NOW = datetime(2026, 9, 24)


@dataclass
class ToolContext:
    participant_id: str | None
    lang: str = "ar"
    wallet: float = 0.0
    ui_blocks: list[dict] = field(default_factory=list)
    seen: dict[str, list[str]] = field(default_factory=dict)  # campaign_id -> titles (ar, en) from tool results
    shown: bool = False                                         # did the agent render cards itself?


def _campaigns(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    conn = connect()
    q = ",".join("?" * len(ids))
    rows = conn.execute(CAMPAIGN_SELECT + f" WHERE c.id IN ({q})", ids).fetchall()
    conn.close()
    return {r["id"]: row_to_campaign(r) for r in rows}


def _l(ctx: ToolContext, c: dict, ar: str, en: str):
    return (c.get(en) or c.get(ar)) if ctx.lang == "en" else c.get(ar)


def _brief(ctx: ToolContext, c: dict) -> dict:
    return {
        "campaign_id": c["id"], "title": _l(ctx, c, "titleAr", "titleEn"),
        "category": _l(ctx, c, "categoryNameAr", "categoryNameEn"),
        "charity": _l(ctx, c, "charity", "charityEn"), "charity_id": c["charityId"],
        "region": _l(ctx, c, "region", "regionEn"),
        "progress_pct": c["progressPct"], "remaining_sar": round(c["remainingAmount"]),
        "unit": _l(ctx, c, "unitAr", "unitEn"), "unit_cost_sar": c["unitCost"],
        "zakat_eligible": c["isZakat"], "waqf": c["isWaqf"],
        "min_amount": c["minDonation"], "ends_at": (c["endsAt"] or "")[:10],
    }


def _allocations(ctx: ToolContext) -> tuple[list[dict], float]:
    if not ctx.participant_id:
        return [], 0.0
    from .. import studydb
    with studydb.connect() as db:
        rows = db.all("SELECT campaign_id, amount FROM allocations WHERE participant_id=?", (ctx.participant_id,))
    return rows, sum(r["amount"] for r in rows)


# ------------------------------------------------------------ information
def search_campaigns(ctx: ToolContext, query: str = "", category: str = "", region: str = "",
                     zakat_only: bool = False, waqf_only: bool = False,
                     near_complete_only: bool = False, limit: int = 8) -> dict:
    from ..search import rank
    from ..seed.en import REGIONS_EN
    limit = max(1, min(int(limit or 8), 15))
    ignored = []
    # Only apply filters that can match something. Models often pass a country
    # ("Saudi Arabia") as a region or invent a category id, which silently
    # empties the result.
    conn = connect()
    valid_cats = {r[0] for r in conn.execute("SELECT id FROM categories")}
    conn.close()
    if category and category not in valid_cats:
        ignored.append(f"category '{category}' is not a category id (see list_categories)"); category = ""
    ar_region = ""
    if region:
        ar_region = next((a for a, e in REGIONS_EN.items()
                          if region.strip().lower() in (a, e.lower()) or a in region or e.lower() in region.lower()), "")
        if not ar_region:
            ignored.append(f"region '{region}' is not a Saudi province with campaigns; searched all regions")
            region = ""
    where, args = ["c.status='active'"], []
    if category:
        where.append("c.category_id=?"); args.append(category)
    if ar_region:
        where.append("c.region=?"); args.append(ar_region)
    if zakat_only:
        where.append("c.is_zakat=1")
    if waqf_only:
        where.append("c.is_waqf=1")
    if near_complete_only:
        where.append("c.raised_amount/c.goal_amount >= 0.9")
    conn = connect()
    rows = {r["id"]: r for r in conn.execute(f"{CAMPAIGN_SELECT} WHERE {' AND '.join(where)}", args)}
    conn.close()

    if query.strip():
        order = [cid for cid, _ in rank(query, list(rows), limit)]
    else:
        order = sorted(rows, key=lambda i: -(rows[i]["raised_amount"] / rows[i]["goal_amount"]))[:limit]
    found = [_brief(ctx, row_to_campaign(rows[i])) for i in order]
    note = {"ignored_filters": ignored} if ignored else {}
    if found:
        return {"count": len(found), "campaigns": found, **note}

    filters = {k: v for k, v in dict(category=category, region=region, zakat_only=zakat_only,
                                     waqf_only=waqf_only, near_complete_only=near_complete_only).items() if v}
    if query and filters:
        loose = search_campaigns(ctx, query=query, limit=limit)
        return {"count": 0, "campaigns": [], "filters_applied": filters,
                "matches_without_filters": loose["campaigns"],
                "hint": "Nothing matches with these filters. Only apply zakat/waqf filters if the participant asked "
                        "for them; otherwise present matches_without_filters. If they did ask, say which "
                        "matches are excluded and why.", **note}
    return {"count": 0, "campaigns": [], "hint": "No match. Try different words, or a category id from list_categories."}


def get_campaign_details(ctx: ToolContext, campaign_id: str) -> dict:
    c = _campaigns([campaign_id]).get(campaign_id)
    if not c:
        return {"error": f"campaign '{campaign_id}' not found"}
    conn = connect()
    ups = conn.execute("SELECT text_ar, text_en, created_at FROM campaign_updates WHERE campaign_id=? "
                       "ORDER BY created_at DESC LIMIT 4", (campaign_id,)).fetchall()
    conn.close()
    out = _brief(ctx, c)
    out.update({
        "description": _l(ctx, c, "descriptionAr", "descriptionEn"),
        "goal_sar": c["goalAmount"], "raised_sar": round(c["raisedAmount"]), "beneficiaries": c["beneficiaries"],
        "zakat_category": _l(ctx, c, "zakatCategory", "zakatCategoryEn"), "launched": c["createdAt"][:10],
        "latest_updates": [{"date": u["created_at"][:10],
                            "text": (u["text_en"] or u["text_ar"]) if ctx.lang == "en" else u["text_ar"]} for u in ups],
    })
    return out


def get_charity_profile(ctx: ToolContext, charity_id: str) -> dict:
    conn = connect()
    r = conn.execute("SELECT * FROM charities WHERE id=? OR name_ar LIKE ? OR name_en LIKE ?",
                     (charity_id, f"%{charity_id}%", f"%{charity_id}%")).fetchone()
    if not r:
        conn.close()
        return {"error": f"charity '{charity_id}' not found"}
    active = conn.execute("SELECT id, title_ar, title_en FROM campaigns WHERE charity_id=? AND status='active'",
                          (r["id"],)).fetchall()
    conn.close()
    en = ctx.lang == "en"
    from ..seed.en import REGIONS_EN
    return {
        "charity_id": r["id"], "name": r["name_en"] if en else r["name_ar"],
        "license_no": r["license_no"], "founded": r["founded_year"], "years_active": NOW.year - r["founded_year"],
        "headquarters": REGIONS_EN.get(r["hq_region"], r["hq_region"]) if en else r["hq_region"],
        "about": r["description_en"] if en else r["description_ar"],
        "governance_score_out_of_100": r["governance_score"], "admin_overhead_pct": r["overhead_pct"],
        "latest_audited_statement": r["audited_year"] or "not published",
        "beneficiaries_last_year": r["beneficiaries_last_year"],
        "active_campaigns": [{"campaign_id": a["id"], "title": a["title_en"] if en else a["title_ar"]} for a in active],
    }


def estimate_impact(ctx: ToolContext, campaign_id: str, amount_sar: float) -> dict:
    c = _campaigns([campaign_id]).get(campaign_id)
    if not c:
        return {"error": f"campaign '{campaign_id}' not found"}
    amount = float(amount_sar)
    if amount < c["minDonation"]:
        return {"error": f"minimum amount for this campaign is {c['minDonation']} virtual SAR"}
    units = amount / c["unitCost"] if c["unitCost"] else None
    remaining = c["remainingAmount"]
    out = {
        "campaign_id": campaign_id, "title": _l(ctx, c, "titleAr", "titleEn"), "amount_sar": amount,
        "unit": _l(ctx, c, "unitAr", "unitEn"), "unit_cost_sar": c["unitCost"],
        "units_funded": round(units, 2) if units is not None else None,
        "share_of_remaining_pct": round(min(100.0, amount / remaining * 100), 1) if remaining else 100.0,
        "would_complete_campaign": amount >= remaining,
        "remaining_after_sar": round(max(0.0, remaining - amount)),
    }
    if c["isWaqf"]:
        out["waqf_note"] = "Endowment: principal is preserved; an estimated ~5% annual yield is spent on the cause indefinitely."
        out["estimated_annual_yield_sar"] = round(amount * 0.05)
    ctx.ui_blocks.append({"kind": "impact", "campaign": c, "impact": out})
    return out


def zakat_calculator(ctx: ToolContext, zakatable_wealth_sar: float) -> dict:
    nisab = round(85 * GOLD_PRICE_SAR_PER_GRAM)
    w = float(zakatable_wealth_sar)
    return {
        "zakatable_wealth_sar": w, "nisab_sar_approx": nisab,
        "nisab_basis": f"85 g of gold at an assumed {GOLD_PRICE_SAR_PER_GRAM:.0f} SAR/g — approximate, check today's price",
        "above_nisab": w >= nisab, "zakat_due_sar": round(w * 0.025, 2) if w >= nisab else 0,
        "rate": "2.5% of zakatable wealth held for one lunar year (hawl)",
        "guidance": "For complex cases refer to ZATCA's zakat calculator or a qualified scholar.",
    }


def get_wallet(ctx: ToolContext) -> dict:
    allocs, spent = _allocations(ctx)
    found = _campaigns([a["campaign_id"] for a in allocs])
    return {
        "currency": "virtual SAR (not real money)", "starting_balance": ctx.wallet,
        "allocated": spent, "remaining": ctx.wallet - spent,
        "allocations": [{"campaign_id": a["campaign_id"], "amount": a["amount"],
                         "title": _l(ctx, found[a["campaign_id"]], "titleAr", "titleEn") if a["campaign_id"] in found else ""}
                        for a in allocs],
    }


def list_categories(ctx: ToolContext) -> dict:
    conn = connect()
    cats = conn.execute("SELECT id, name_ar, name_en FROM categories ORDER BY sort").fetchall()
    conn.close()
    from ..seed.en import REGIONS_EN
    en = ctx.lang == "en"
    return {"categories": [{"id": c["id"], "name": c["name_en"] if en else c["name_ar"]} for c in cats],
            "regions": list(REGIONS_EN.values()) if en else list(REGIONS_EN.keys())}


# ----------------------------------------------------------- presentation
def show_campaigns(ctx: ToolContext, campaign_ids: list[str], heading: str = "") -> dict:
    found = _campaigns(list(dict.fromkeys(campaign_ids))[:6])
    ordered = [found[i] for i in campaign_ids if i in found]
    if ordered:
        ctx.ui_blocks.append({"kind": "campaigns", "heading": heading, "campaigns": ordered})
    return {"shown": [c["id"] for c in ordered], "not_found": [i for i in campaign_ids if i not in found]}


def show_comparison(ctx: ToolContext, campaign_ids: list[str]) -> dict:
    ids = list(dict.fromkeys(campaign_ids))[:4]
    found = _campaigns(ids)
    conn = connect()
    rows = []
    for cid in ids:
        c = found.get(cid)
        if not c:
            continue
        ch = conn.execute("SELECT governance_score, overhead_pct, audited_year, founded_year FROM charities WHERE id=?",
                          (c["charityId"],)).fetchone()
        rows.append({**_brief(ctx, c),
                     "charity_governance_score": ch["governance_score"] if ch else None,
                     "charity_overhead_pct": ch["overhead_pct"] if ch else None,
                     "charity_audited_year": ch["audited_year"] if ch else None,
                     "charity_founded": ch["founded_year"] if ch else None})
    alternatives = []
    for cat_id in dict.fromkeys(found[r["campaign_id"]]["categoryId"] for r in rows):
        q = ",".join("?" * len(ids))
        alt = conn.execute(
            f"{CAMPAIGN_SELECT} WHERE c.status='active' AND c.category_id=? AND c.id NOT IN ({q}) "
            "ORDER BY c.raised_amount/c.goal_amount DESC LIMIT 2", (cat_id, *ids)).fetchall()
        if alt:
            alternatives.append({"categoryId": cat_id, "categoryAr": alt[0]["category_name_ar"],
                                 "categoryEn": alt[0]["category_name_en"],
                                 "campaigns": [row_to_campaign(a) for a in alt]})
    conn.close()
    if len(rows) >= 2:
        ctx.ui_blocks.append({"kind": "comparison", "rows": rows, "alternatives": alternatives,
                              "campaigns": [found[r["campaign_id"]] for r in rows]})
        return {"compared": rows}
    return {"error": "need at least two valid campaign ids"}


def propose_allocation(ctx: ToolContext, items: list[dict], note: str = "") -> dict:
    _, spent = _allocations(ctx)
    remaining = ctx.wallet - spent
    found = _campaigns([str(i.get("campaign_id", "")) for i in items])
    lines, problems = [], []
    for i in items:
        cid, amt = str(i.get("campaign_id", "")), float(i.get("amount_sar", 0) or 0)
        c = found.get(cid)
        if not c:
            problems.append(f"{cid}: not found"); continue
        if amt < c["minDonation"]:
            problems.append(f"{cid}: below minimum {c['minDonation']}"); continue
        lines.append({"campaign": c, "amount": amt,
                      "units": round(amt / c["unitCost"], 1) if c["unitCost"] else None})
    total = sum(l["amount"] for l in lines)
    if total > remaining + 1e-6:
        return {"error": f"proposal totals {total:.0f} but only {remaining:.0f} virtual SAR remain; reduce the amounts",
                "remaining": remaining}
    if lines:
        ctx.ui_blocks.append({"kind": "allocation", "note": note, "items": lines, "total": total})
    return {"proposed_total": total, "remaining_before": remaining, "items": len(lines), "problems": problems,
            "note_for_agent": "The participant sees the proposal with an 'allocate' button. Do not claim anything was allocated."}


# ------------------------------------------------------------- registry
S = lambda props, req=(): {"type": "object", "properties": props, "required": list(req)}  # noqa: E731
STR, NUM, BOOL = {"type": "string"}, {"type": "number"}, {"type": "boolean"}

TOOLS: dict[str, dict] = {
    "search_campaigns": dict(
        fn=search_campaigns, label_ar="يبحث في فرص التبرع", label_en="Searching campaigns",
        description="Search active charity campaigns by meaning and keywords (Arabic or English), optionally filtered. "
                    "Returns id, title, charity, region, progress, remaining amount, impact unit and cost, zakat/waqf flags.",
        schema=S({"query": {**STR, "description": "what the participant is looking for, in their words"},
                  "category": {**STR, "description": "category id from list_categories, optional"},
                  "region": {**STR, "description": "Saudi region, optional"},
                  "zakat_only": {**BOOL, "description": "only campaigns eligible for zakat"},
                  "waqf_only": {**BOOL, "description": "only endowment (waqf) campaigns"},
                  "near_complete_only": {**BOOL, "description": "only campaigns at 90%+ funded"},
                  "limit": {"type": "integer", "description": "max results (default 8)"}})),
    "get_campaign_details": dict(
        fn=get_campaign_details, label_ar="يقرأ تفاصيل الفرصة وآخر تحديثاتها", label_en="Reading campaign details and updates",
        description="Full facts for one campaign: description, goal, raised, beneficiaries, zakat category, latest field updates.",
        schema=S({"campaign_id": STR}, ["campaign_id"])),
    "get_charity_profile": dict(
        fn=get_charity_profile, label_ar="يراجع ملف الجهة المنفذة", label_en="Checking the charity's record",
        description="Track record of the executing charity: licence, years active, governance score, admin overhead, audited statements, reach.",
        schema=S({"charity_id": {**STR, "description": "charity_id from a campaign result"}}, ["charity_id"])),
    "estimate_impact": dict(
        fn=estimate_impact, label_ar="يحسب أثر المبلغ", label_en="Calculating the impact of an amount",
        description="What a specific amount achieves in a campaign: units funded, share of the remaining gap, waqf yield. Also shows it to the participant.",
        schema=S({"campaign_id": STR, "amount_sar": NUM}, ["campaign_id", "amount_sar"])),
    "zakat_calculator": dict(
        fn=zakat_calculator, label_ar="يحسب الزكاة والنصاب", label_en="Calculating zakat",
        description="ONLY for 'how much zakat do I owe?': nisab and 2.5% due from TOTAL zakatable wealth. "
                    "Do NOT call it when the participant already states an amount of zakat to give.",
        schema=S({"zakatable_wealth_sar": {**NUM, "description": "total zakatable wealth held for a lunar year"}},
                 ["zakatable_wealth_sar"])),
    "get_wallet": dict(
        fn=get_wallet, label_ar="يطّلع على رصيدك الافتراضي", label_en="Checking your virtual balance",
        description="The participant's virtual balance: starting amount, remaining, and what they have allocated so far.",
        schema=S({})),
    "list_categories": dict(
        fn=list_categories, label_ar="يستعرض مجالات التبرع", label_en="Listing causes",
        description="All category ids with names, and regions that have campaigns.",
        schema=S({})),
    "show_campaigns": dict(
        fn=show_campaigns, label_ar="يعرض الفرص المقترحة", label_en="Showing suggested campaigns",
        description="Display campaign cards (max 6). Call this for every campaign you suggest.",
        schema=S({"campaign_ids": {"type": "array", "items": STR},
                  "heading": {**STR, "description": "short heading in the participant's language"}}, ["campaign_ids"])),
    "show_comparison": dict(
        fn=show_comparison, label_ar="يقارن بين الفرص", label_en="Comparing campaigns",
        description="Display a side-by-side comparison of 2-4 campaigns incl. charity governance and overhead, and return the data.",
        schema=S({"campaign_ids": {"type": "array", "items": STR}}, ["campaign_ids"])),
    "propose_allocation": dict(
        fn=propose_allocation, label_ar="يجهّز توزيعاً مقترحاً لرصيدك", label_en="Preparing a suggested allocation",
        description="Propose how to split part or all of the remaining virtual balance across campaigns. "
                    "The participant reviews it and decides; only use when they ask for help splitting their balance.",
        schema=S({"items": {"type": "array", "items": S({"campaign_id": STR, "amount_sar": NUM},
                                                          ["campaign_id", "amount_sar"])},
                  "note": {**STR, "description": "one sentence explaining the split"}}, ["items"])),
}

PRESENTATION = {"show_campaigns", "show_comparison", "propose_allocation"}


def execute(ctx: ToolContext, name: str, args: dict) -> dict:
    spec = TOOLS.get(name)
    if not spec:
        return {"error": f"unknown tool {name}"}
    if name in PRESENTATION:
        ctx.shown = True
    try:
        out = spec["fn"](ctx, **(args or {}))
        _collect(out, ctx.seen)
        return out
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:                      # surface to the model, keep the loop alive
        return {"error": f"{type(e).__name__}: {e}"}


def _collect(x, seen: dict[str, list[str]]) -> None:
    if isinstance(x, dict):
        if "campaign_id" in x and "title" in x:
            seen.setdefault(str(x["campaign_id"]), [])
            if x["title"] not in seen[str(x["campaign_id"])]:
                seen[str(x["campaign_id"])].append(str(x["title"]))
        for v in x.values():
            _collect(v, seen)
    elif isinstance(x, list):
        for v in x:
            _collect(v, seen)


def _mentions(text: str, title: str) -> bool:
    """Full title, or its first two words (models shorten «حفر الآبار وسقيا الماء» to «حفر الآبار»)."""
    if not title:
        return False
    if title.lower() in text.lower():
        return True
    words = title.split()
    return len(words) >= 3 and " ".join(words[:2]).lower() in text.lower()


def ground_cards(ctx: ToolContext, text: str) -> dict | None:
    """Safety net: campaigns the agent named from its own tool results but never displayed."""
    if ctx.shown or not text:
        return None
    ids = [cid for cid, titles in ctx.seen.items() if any(_mentions(text, t) for t in titles)][:4]
    found = _campaigns(ids)
    cards = [found[i] for i in ids if i in found]
    return {"kind": "campaigns", "heading": "", "campaigns": cards} if cards else None


def dumps(x) -> str:
    return json.dumps(x, ensure_ascii=False, default=str)
