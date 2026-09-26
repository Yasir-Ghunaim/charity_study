"""Recommendation, agent and evaluation endpoints."""
from __future__ import annotations

from datetime import datetime

import numpy as np
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..db import CAMPAIGN_SELECT, connect, row_to_campaign
import json

from fastapi.responses import StreamingResponse

from ..agent import assistant
from ..agent.nudge import plan as nudge_plan
from ..rec.store import get_store
from ..rec.strategies import STRATEGIES, hybrid

router = APIRouter()
NOW = datetime(2026, 9, 24)


def _hydrate(recs) -> list[dict]:
    if not recs:
        return []
    ids = [r.campaign_id for r in recs]
    conn = connect()
    q = ",".join("?" * len(ids))
    rows = {r["id"]: r for r in conn.execute(CAMPAIGN_SELECT + f" WHERE c.id IN ({q})", ids)}
    conn.close()
    out = []
    for r in recs:
        if r.campaign_id not in rows:
            continue
        c = row_to_campaign(rows[r.campaign_id])
        c["recScore"] = round(r.score, 4)
        c["recReasons"] = r.reasons
        c["recComponents"] = r.components
        out.append(c)
    return out


@router.get("/recommendations")
def recommendations(
    user: str | None = None,
    strategy: str = Query("hybrid", pattern="^(hybrid|cf|content|popularity)$"),
    k: int = Query(8, ge=1, le=24),
    intent: str | None = Query(None, pattern="^(zakat|waqf)$"),
    category: str | None = None,
    max_repeat: int | None = Query(None, ge=0, le=24),
):
    store = get_store()
    fn = STRATEGIES[strategy]
    kw = dict(user_id=user or "anonymous", k=k)
    if strategy == "hybrid":
        kw.update(intent=intent, category=category, now=NOW, max_repeat=max_repeat)
    recs = fn(store, **kw)
    return {"strategy": strategy, "userId": user,
            "coldStart": user is None or store.uidx.get(user) is None,
            "items": _hydrate(recs)}


@router.get("/recommendations/similar/{campaign_id}")
def similar(campaign_id: str, k: int = Query(4, ge=1, le=12)):
    """Item-to-item 'فرص مشابهة' for the campaign detail page."""
    store = get_store()
    i = store.iidx.get(campaign_id)
    if i is None:
        return {"items": []}
    blend = 0.6 * store.item_sim_cf[i] + 0.4 * store.item_sim_content[i]
    order = [j for j in np.argsort(-blend)[:k]]
    conn = connect()
    ids = [store.items[j] for j in order]
    q = ",".join("?" * len(ids))
    rows = {r["id"]: r for r in conn.execute(CAMPAIGN_SELECT + f" WHERE c.id IN ({q})", ids)}
    conn.close()
    items = []
    for j in order:
        cid = store.items[j]
        if cid in rows:
            c = row_to_campaign(rows[cid])
            c["similarity"] = round(float(blend[j]), 4)
            items.append(c)
    return {"items": items}


@router.get("/nudge/{user_id}")
def nudge(user_id: str):
    return nudge_plan(user_id)


class ChatIn(BaseModel):
    userId: str | None = None
    message: str
    history: list[dict] = []
    engine: str | None = None          # anthropic | ollama | rules; default: best available
    campaignId: str | None = None      # set when asking from a campaign page


@router.get("/agent/engines")
def engines():
    return assistant.available_engines()


@router.post("/agent/stream")
def agent_stream(body: ChatIn):
    """Server-sent events: one `data:` line per agent event."""
    def gen():
        for ev in assistant.run(body.userId, body.message, body.history, body.engine, body.campaignId):
            yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/agent/chat")
def agent_chat(body: ChatIn):
    """Same as /agent/stream but collected into one response."""
    return {"events": list(assistant.run(body.userId, body.message, body.history, body.engine, body.campaignId))}


@router.get("/eval")
def run_eval(k: int = Query(10, ge=1, le=20)):
    from ..rec.evaluate import evaluate
    return evaluate(k=k)


@router.get("/search/status")
def search_status():
    from ..search import status
    return status()


@router.get("/debug/store")
def store_stats():
    return get_store().stats()
