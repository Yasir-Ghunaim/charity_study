"""Recommendation strategies, from trivial baseline to the production hybrid.

Every strategy returns a list of Rec objects carrying a score *and* a reason —
the reason is what the UI renders as "لماذا اقترحنا هذا؟" and what the agent
quotes when it explains a basket.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from ..seed.generate import seasonal_multiplier, in_ramadan
from .store import RecStore, get_store

NOW = datetime(2026, 9, 24)


@dataclass
class Rec:
    campaign_id: str
    score: float
    base_score: float = 0.0
    reasons: list[dict] = field(default_factory=list)
    components: dict = field(default_factory=dict)

    def add(self, code: str, text_ar: str, weight: float = 1.0) -> None:
        self.reasons.append({"code": code, "textAr": text_ar, "weight": round(weight, 3)})


def _norm(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    return np.zeros_like(x) if hi - lo < 1e-9 else (x - lo) / (hi - lo)


# --------------------------------------------------------------- baseline: pop
def popularity(store: RecStore, user_id: str | None = None, k: int = 10, **_) -> list[Rec]:
    order = np.argsort(-store.pop)[:k]
    return [Rec(store.items[i], float(store.pop[i]),
                [{"code": "popular", "textAr": "من أكثر الفرص تفاعلاً هذا الشهر", "weight": 1.0}])
            for i in order]


# ------------------------------------------------------------ content-based
def content_based(store: RecStore, user_id: str, k: int = 10, **_) -> list[Rec]:
    profile = store.content_profile(user_id)
    if profile is None:
        return popularity(store, user_id, k)
    scores = store.tfidf @ profile
    seen = store.donated_items(user_id)
    recs = []
    for i in np.argsort(-scores):
        cid = store.items[i]
        if cid in seen:
            continue
        r = Rec(cid, float(scores[i]))
        anchor = _closest_donated(store, user_id, cid, kind="content")
        if anchor:
            r.add("content_similar", f"يشبه «{store.campaigns[anchor]['title_ar']}» الذي دعمته سابقاً")
        recs.append(r)
        if len(recs) >= k:
            break
    return recs


# --------------------------------------------------------- item-item CF
def item_cf(store: RecStore, user_id: str, k: int = 10, **_) -> list[Rec]:
    v = store.user_vector(user_id)
    if v is None or v.sum() == 0:
        return popularity(store, user_id, k)
    scores = v @ store.item_sim_cf
    seen = store.donated_items(user_id)
    recs = []
    for i in np.argsort(-scores):
        cid = store.items[i]
        if cid in seen or scores[i] <= 0:
            continue
        r = Rec(cid, float(scores[i]))
        anchor = _closest_donated(store, user_id, cid, kind="cf")
        if anchor:
            r.add("cf_similar",
                  f"متبرعون دعموا «{store.campaigns[anchor]['title_ar']}» دعموا هذه الفرصة أيضاً")
        recs.append(r)
        if len(recs) >= k:
            break
    return recs


def _closest_donated(store: RecStore, user_id: str, cid: str, kind: str) -> str | None:
    """Which past gift best explains this suggestion?"""
    S = store.item_sim_content if kind == "content" else store.item_sim_cf
    j = store.iidx[cid]
    best, best_s = None, 0.0
    for prev in store.donated_items(user_id):
        i = store.iidx.get(prev)
        if i is None:
            continue
        if S[i, j] > best_s:
            best, best_s = prev, float(S[i, j])
    return best


# ------------------------------------------------------------------- hybrid
# Tuned on the validation window (train < 2026-03-24, score Mar 24-Jun 24);
# see app/rec/evaluate.py. Content matters as much as CF here because the
# catalogue is small and titles/tags carry strong intent (أيتام, وقف, زكاة).
DEFAULT_WEIGHTS = {"cf": 0.35, "content": 0.35, "popularity": 0.10,
                   "seasonal": 0.12, "urgency": 0.08}

# A third of the catalogue sits above 90% funded, so a broad urgency bonus
# floods the feed with almost-closed campaigns and starves newer ones. Kick in
# late, and cap how many can occupy a single result set.
URGENCY_FLOOR = 0.93
MAX_NEAR_COMPLETE = 3

# Half of all gifts are repeats to a campaign the donor already supports, and
# the collaborative score naturally ranks those highest. Left alone, the feed
# becomes a "give again" list with little discovery. Cap the repeat slots.
MAX_REPEAT = 4


def hybrid(store: RecStore, user_id: str | None = None, k: int = 10,
           intent: str | None = None, category: str | None = None,
           exclude: set[str] | None = None, weights: dict | None = None,
           diversity: float = 0.15, now: datetime = NOW,
           max_repeat: int | None = None, **_) -> list[Rec]:
    """Blended ranker plus the rules a donation platform actually needs."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    n = len(store.items)
    exclude = set(exclude or ())

    v = store.user_vector(user_id) if user_id else None
    cold = v is None or v.sum() == 0

    cf = _norm(v @ store.item_sim_cf) if not cold else np.zeros(n)
    profile = store.content_profile(user_id) if user_id else None
    content = _norm(store.tfidf @ profile) if profile is not None else np.zeros(n)
    pop = store.pop.copy()

    seasonal = np.zeros(n)
    urgency = np.zeros(n)
    for i, cid in enumerate(store.items):
        c = store.campaigns[cid]
        seasonal[i] = min(4.0, seasonal_multiplier(now, c["category_id"])) / 4.0
        pct = c["raised_amount"] / c["goal_amount"] if c["goal_amount"] else 0
        # campaigns on the cusp of completion convert best -> deliberate boost
        urgency[i] = (pct - URGENCY_FLOOR) / (1.0 - URGENCY_FLOOR) if pct >= URGENCY_FLOOR else 0.0

    if cold:
        # no history: lean on what is popular and in-season
        w = {**w, "cf": 0.0, "content": 0.0, "popularity": 0.55, "seasonal": 0.30, "urgency": 0.15}

    base = (w["cf"] * cf + w["content"] * content + w["popularity"] * pop
            + w["seasonal"] * seasonal + w["urgency"] * urgency)

    # ---- hard filters
    recent_cut = (now - timedelta(days=30)).isoformat()
    recent = set()
    for d in store.user_donations.get(user_id or "", []):
        if d["created_at"] >= recent_cut and not d["is_recurring"]:
            recent.add(d["campaign_id"])

    mask = np.ones(n, dtype=bool)
    for i, cid in enumerate(store.items):
        c = store.campaigns[cid]
        if cid in exclude or cid in recent or c["status"] != "active":
            mask[i] = False
        if intent == "zakat" and not c["is_zakat"]:
            mask[i] = False
        if intent == "waqf" and not c["is_waqf"]:
            mask[i] = False
        if category and c["category_id"] != category:
            mask[i] = False
    base = np.where(mask, base, -1e9)

    # ---- greedy MMR: pick high scorers that are unlike what is already picked
    near = np.array([
        (store.campaigns[cid]["raised_amount"] / store.campaigns[cid]["goal_amount"]
         if store.campaigns[cid]["goal_amount"] else 0) >= URGENCY_FLOOR
        for cid in store.items])

    history = store.donated_items(user_id) if user_id else set()
    is_repeat = np.array([cid in history for cid in store.items])
    cap_repeat = MAX_REPEAT if max_repeat is None else max_repeat

    picked: list[Rec] = []
    chosen_idx: list[int] = []
    n_near = n_rep = 0
    for _ in range(min(k, int(mask.sum()))):
        adjusted = base.copy()
        if n_near >= MAX_NEAR_COMPLETE:
            adjusted = np.where(near, -1e9, adjusted)
        if n_rep >= cap_repeat:
            adjusted = np.where(is_repeat, -1e9, adjusted)
        if chosen_idx and diversity > 0:
            sim_to_picked = store.item_sim_content[:, chosen_idx].max(axis=1)
            adjusted = adjusted - diversity * sim_to_picked
        for i in chosen_idx:
            adjusted[i] = -1e9
        i = int(np.argmax(adjusted))
        if adjusted[i] <= -1e8:
            break
        chosen_idx.append(i)
        if near[i]:
            n_near += 1
        if is_repeat[i]:
            n_rep += 1

        cid = store.items[i]
        c = store.campaigns[cid]
        # rank by the diversity-adjusted score, but keep the raw blend for debugging
        r = Rec(cid, float(adjusted[i]), base_score=float(base[i]), components={
            "cf": round(float(cf[i]), 3), "content": round(float(content[i]), 3),
            "popularity": round(float(pop[i]), 3), "seasonal": round(float(seasonal[i]), 3),
            "urgency": round(float(urgency[i]), 3)})

        if is_repeat[i]:
            r.add("renew", "سبق أن دعمت هذه الفرصة — جدّد عطاءك", 1.0)

        # reasons, strongest signal first
        ranked = sorted(r.components.items(), key=lambda kv: -kv[1] * w.get(kv[0], 0))
        for name, val in ranked[:2]:
            if val <= 0.05:
                continue
            if name == "cf":
                a = _closest_donated(store, user_id, cid, "cf")
                if a:
                    r.add("cf_similar",
                          f"متبرعون يشبهونك دعموا «{store.campaigns[a]['title_ar']}» وهذه الفرصة", val)
            elif name == "content":
                a = _closest_donated(store, user_id, cid, "content")
                if a:
                    r.add("content_similar",
                          f"قريبة من «{store.campaigns[a]['title_ar']}» الذي سبق أن دعمته", val)
            elif name == "urgency":
                pct = round(c["raised_amount"] / c["goal_amount"] * 100)
                r.add("near_complete", f"شارفت على الإكتمال — تبقّى {100 - pct}% فقط لإغلاقها", val)
            elif name == "seasonal":
                if in_ramadan(now):
                    r.add("seasonal", "مضاعفة الأجر في موسم رمضان", val)
                else:
                    r.add("seasonal", f"في موسمها الآن ({c['category_name_ar']})", val)
            elif name == "popularity":
                r.add("popular", "من أكثر الفرص تفاعلاً هذا الشهر", val)
        if not r.reasons:
            r.add("explore", f"فرصة جديدة في {c['category_name_ar']} قد تهمّك", 0.2)
        picked.append(r)

    return picked


STRATEGIES = {
    "popularity": popularity,
    "content": content_based,
    "cf": item_cf,
    "hybrid": hybrid,
}


def recommend(strategy: str = "hybrid", **kw) -> list[Rec]:
    store = get_store()
    fn = STRATEGIES.get(strategy, hybrid)
    return fn(store, **kw)
