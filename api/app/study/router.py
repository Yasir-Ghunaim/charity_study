"""Study API: consent → pre-survey → allocate with the agent → post-survey.

The participant is identified by an httpOnly cookie set at join. Every
endpoint derives the participant from that cookie, never from the request
body. Admin export is protected by STUDY_ADMIN_TOKEN.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import studydb
from ..agent import assistant
from ..db import CAMPAIGN_SELECT, connect, row_to_campaign
from . import config as C

router = APIRouter(prefix="/study", tags=["study"])
COOKIE = "study_pid"
PREVIEW_COOKIE = "study_preview"       # set from /admin: lets the admin run a study without counting as data


def _preview_sig(study_id: str) -> str | None:
    token = os.environ.get("STUDY_ADMIN_TOKEN")
    if not token:
        return None
    return hmac.new(token.encode(), f"preview:{study_id}".encode(), hashlib.sha256).hexdigest()[:32]


def _preview_study(request: Request) -> str | None:
    """The study id this browser may preview, if it holds a valid preview cookie."""
    raw = request.cookies.get(PREVIEW_COOKIE) or ""
    sid, _, sig = raw.rpartition(".")
    good = _preview_sig(sid) if sid else None
    return sid if good and secrets.compare_digest(good, sig) else None


def _cookie_kw(request: Request) -> dict:
    return {"httponly": True, "samesite": "lax", "path": "/",
            "secure": request.headers.get("x-forwarded-proto") == "https"}


def _delete_participant(db, pid: str) -> None:
    for t in ("survey_responses", "allocations", "study_events", "agent_turns"):
        db.execute(f"DELETE FROM {t} WHERE participant_id=?", (pid,))
    db.execute("DELETE FROM participants WHERE id=?", (pid,))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _participant(request: Request, required: bool = True) -> dict | None:
    pid = request.cookies.get(COOKIE)
    row = None
    if pid:
        with studydb.connect() as db:
            row = db.one("""SELECT p.*, s.mode AS mode, s.max_turns AS max_turns, s.pre_survey AS pre_survey,
                                   s.post_survey AS post_survey, s.status AS study_status
                            FROM participants p LEFT JOIN studies s ON s.id = p.study_id WHERE p.id=?""", (pid,))
    if row is None or row["status"] == "withdrawn":
        if required:
            raise HTTPException(401, "not a participant")
        return None
    p = dict(row)
    p["mode"] = p.get("mode") or "assistant"                  # participants from before multi-study support
    p["max_turns"] = p.get("max_turns") or C.DEFAULT_MAX_TURNS
    p["pre_survey"] = bool(p["pre_survey"]) if p.get("pre_survey") is not None else True
    p["post_survey"] = bool(p["post_survey"]) if p.get("post_survey") is not None else True
    return p


def _study(study_id: str) -> dict | None:
    with studydb.connect() as db:
        return db.one("SELECT * FROM studies WHERE id=?", (study_id,))


def _study_public(s: dict) -> dict:
    return {"id": s["id"], "status": s["status"], "mode": s["mode"], "wallet": s["wallet"],
            "maxTurns": s["max_turns"], "preSurvey": bool(s["pre_survey"]), "postSurvey": bool(s["post_survey"]),
            "consent": C.consent_for(s["mode"], s["wallet"])}


def campaigns_by_id(ids: list[str]) -> dict[str, dict]:
    """Catalogue lookup (separate database from the study data)."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return {}
    conn = connect()
    rows = conn.execute(CAMPAIGN_SELECT + f" WHERE c.id IN ({','.join('?' * len(ids))})", ids).fetchall()
    conn.close()
    return {r["id"]: row_to_campaign(r) for r in rows}


def _wallet(pid: str, start: float) -> dict:
    with studydb.connect() as db:
        rows = db.all("SELECT campaign_id, amount FROM allocations WHERE participant_id=? ORDER BY created_at", (pid,))
    found = campaigns_by_id([r["campaign_id"] for r in rows])
    items = [{"campaign": found[r["campaign_id"]], "amount": r["amount"]} for r in rows if r["campaign_id"] in found]
    spent = sum(i["amount"] for i in items)
    return {"start": start, "allocated": spent, "remaining": start - spent, "items": items}


def _log(pid: str, type_: str, campaign_id: str | None = None, payload: dict | None = None,
         client_ts: str | None = None) -> None:
    with studydb.connect() as db:
        db.execute("INSERT INTO study_events (participant_id,type,campaign_id,payload,client_ts,created_at) "
                   "VALUES (?,?,?,?,?,?)", (pid, type_, campaign_id,
                                            json.dumps(payload, ensure_ascii=False) if payload else None,
                                            client_ts, _now()))


def _public(p: dict) -> dict:
    return {"code": p["code"], "nickname": p["nickname"], "lang": p["lang"], "status": p["status"],
            "preview": bool(p.get("is_preview")),
            "study": {"id": p.get("study_id"), "mode": p["mode"], "maxTurns": p["max_turns"],
                      "preSurvey": p["pre_survey"], "postSurvey": p["post_survey"],
                      "assistant": C.MODES[p["mode"]]["assistant"], "browse": C.MODES[p["mode"]]["browse"]}}


# ------------------------------------------------------------ public study
@router.get("/s/{study_id}")
def public_study(study_id: str, request: Request):
    st = _study(study_id)
    if not st:
        raise HTTPException(404, "study not found")
    return {**_study_public(st), "preview": _preview_study(request) == study_id}


@router.get("/open")
def open_studies():
    """Lets the bare site address forward to the study when exactly one is open."""
    with studydb.connect() as db:
        return {"open": [r["id"] for r in db.all("SELECT id FROM studies WHERE status='open' ORDER BY created_at")]}


# -------------------------------------------------------------------- join
class JoinIn(BaseModel):
    studyId: str = Field(min_length=1, max_length=40)
    nickname: str = Field(min_length=2, max_length=24)
    lang: str = Field(pattern="^(ar|en)$")
    adult: bool
    consent: bool
    consentVersion: str


@router.post("/join")
def join(body: JoinIn, request: Request, response: Response):
    if not (body.adult and body.consent):
        raise HTTPException(400, "consent and age confirmation are required")
    st = _study(body.studyId)
    if not st:
        raise HTTPException(404, "study not found")
    preview = _preview_study(request) == st["id"]
    if st["status"] != "open" and not preview:
        raise HTTPException(409, "this study is not accepting participants")
    consent = C.consent_for(st["mode"], st["wallet"])
    if body.consentVersion != consent["version"]:
        raise HTTPException(409, "consent text changed; reload the page")
    nick = " ".join(body.nickname.split())
    pid = str(uuid.uuid4())
    code = secrets.token_hex(3).upper()                     # e.g. 4F9A2C
    has_ai = C.MODES[st["mode"]]["assistant"]
    engine = assistant.pick_engine() if has_ai else None
    agent_config = {"engine": engine, "model": assistant.model_for(engine) if engine else None,
                    "promptVersion": assistant.PROMPT_VERSION if has_ai else None,
                    "surveyVersion": C.SURVEY_VERSION}
    now = _now()
    status = "consented" if st["pre_survey"] else "pre_done"
    with studydb.connect() as db:
        db.execute(
            """INSERT INTO participants (id,study_id,code,nickname,lang,condition,consent_version,consented_at,status,
               wallet_start,agent_config,pre_done_at,user_agent,is_preview) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, st["id"], code, nick, body.lang, st["mode"], consent["version"], now, status, st["wallet"],
             json.dumps(agent_config), None if st["pre_survey"] else now,
             (request.headers.get("user-agent") or "")[:200], int(preview)))
    response.set_cookie(COOKIE, pid, max_age=60 * 60 * 24 * 7, **_cookie_kw(request))
    _log(pid, "join", payload={"lang": body.lang, "study": st["id"], "preview": preview})
    return {"ok": True, "code": code}


@router.get("/me")
def me(request: Request):
    p = _participant(request)
    return {**_public(p), "wallet": _wallet(p["id"], p["wallet_start"])}


class LangIn(BaseModel):
    lang: str = Field(pattern="^(ar|en)$")


@router.post("/lang")
def set_lang(body: LangIn, request: Request):
    p = _participant(request)
    with studydb.connect() as db:
        db.execute("UPDATE participants SET lang=? WHERE id=?", (body.lang, p["id"]))
    _log(p["id"], "lang_switch", payload={"from": p["lang"], "to": body.lang})
    return {"ok": True}


# ----------------------------------------------------------------- surveys
@router.get("/survey/{phase}")
def survey(phase: str, request: Request):
    p = _participant(request)
    if phase not in ("pre", "post"):
        raise HTTPException(404)
    return {"phase": phase, "version": C.SURVEY_VERSION, "questions": C.survey_for(phase, p["mode"])}


class SurveyIn(BaseModel):
    answers: dict


@router.post("/survey/{phase}")
def submit_survey(phase: str, body: SurveyIn, request: Request):
    p = _participant(request)
    if phase not in ("pre", "post"):
        raise HTTPException(404)
    expected = "consented" if phase == "pre" else "finished"
    if p["status"] != expected:
        raise HTTPException(409, f"this survey is not open (status={p['status']})")
    clean = {}
    for q in C.survey_for(phase, p["mode"]):
        qid = q["id"]
        a = body.answers.get(qid)
        if a in (None, "", []):
            if q["required"]:
                raise HTTPException(400, f"missing answer: {qid}")
            continue
        valid = {o["value"] for o in q.get("options", [])}
        if q["type"] in ("single", "likert") and a not in valid:
            raise HTTPException(400, f"invalid answer for {qid}")
        if q["type"] == "multi" and (not isinstance(a, list) or not set(a) <= valid):
            raise HTTPException(400, f"invalid answer for {qid}")
        if q["type"] == "text":
            a = str(a)[:2000]
        clean[qid] = a
    with studydb.connect() as db:
        db.execute("""INSERT INTO survey_responses (participant_id,phase,answers,created_at) VALUES (?,?,?,?)
                      ON CONFLICT (participant_id, phase) DO UPDATE SET answers=excluded.answers,
                      created_at=excluded.created_at""",
                   (p["id"], phase, json.dumps(clean, ensure_ascii=False), _now()))
        if phase == "pre":
            db.execute("UPDATE participants SET status='pre_done', pre_done_at=? WHERE id=?", (_now(), p["id"]))
        else:
            db.execute("UPDATE participants SET status='completed', completed_at=? WHERE id=?", (_now(), p["id"]))
    _log(p["id"], f"survey_{phase}_submitted")
    return {"ok": True}


# ------------------------------------------------------------- allocations
class AllocIn(BaseModel):
    campaignId: str
    amount: float = Field(ge=0)
    source: str = Field(default="card", max_length=40)


def _set_allocation(p: dict, campaign_id: str, amount: float, source: str) -> dict:
    c = campaigns_by_id([campaign_id]).get(campaign_id)
    if not c:
        raise HTTPException(404, "campaign not found")
    if amount > 0 and amount < c["minDonation"]:
        raise HTTPException(400, f"minimum is {c['minDonation']:.0f}")
    with studydb.connect() as db:
        prev = db.one("SELECT amount FROM allocations WHERE participant_id=? AND campaign_id=?", (p["id"], campaign_id))
        others = db.value("SELECT COALESCE(SUM(amount),0) AS s FROM allocations WHERE participant_id=? AND campaign_id<>?",
                          (p["id"], campaign_id))
        if others + amount > p["wallet_start"] + 1e-6:
            raise HTTPException(400, f"not enough balance (remaining {p['wallet_start'] - others:.0f})")
        now = _now()
        if amount == 0:
            db.execute("DELETE FROM allocations WHERE participant_id=? AND campaign_id=?", (p["id"], campaign_id))
        else:
            db.execute("""INSERT INTO allocations (participant_id,campaign_id,amount,source,created_at,updated_at)
                          VALUES (?,?,?,?,?,?) ON CONFLICT (participant_id,campaign_id)
                          DO UPDATE SET amount=excluded.amount, source=excluded.source, updated_at=excluded.updated_at""",
                       (p["id"], campaign_id, amount, source, now, now))
    _log(p["id"], "allocate" if amount else "deallocate", campaign_id,
         {"amount": amount, "previous": prev["amount"] if prev else 0, "source": source})
    return _wallet(p["id"], p["wallet_start"])


@router.post("/allocations")
def allocate(body: AllocIn, request: Request):
    p = _participant(request)
    if p["status"] != "pre_done":
        raise HTTPException(409, "allocation is not open (status=%s)" % p["status"])
    return _set_allocation(p, body.campaignId, round(body.amount), body.source)


class BatchIn(BaseModel):
    items: list[AllocIn]


@router.post("/allocations/batch")
def allocate_batch(body: BatchIn, request: Request):
    """Accept an agent proposal: adds each amount to any existing allocation."""
    p = _participant(request)
    if p["status"] != "pre_done":
        raise HTTPException(409, "allocation is closed")
    w = _wallet(p["id"], p["wallet_start"])
    current = {i["campaign"]["id"]: i["amount"] for i in w["items"]}
    if sum(round(i.amount) for i in body.items) > w["remaining"] + 1e-6:
        raise HTTPException(400, "not enough balance")
    for i in body.items:
        w = _set_allocation(p, i.campaignId, current.get(i.campaignId, 0) + round(i.amount), i.source)
    return w


# ------------------------------------------------------------------ events
class EventIn(BaseModel):
    type: str = Field(max_length=40)
    campaignId: str | None = None
    payload: dict | None = None
    clientTs: str | None = None


@router.post("/events")
def event(body: EventIn, request: Request):
    p = _participant(request, required=False)
    if p:
        payload = body.payload if body.payload and len(json.dumps(body.payload)) < 4000 else None
        _log(p["id"], body.type, body.campaignId, payload, body.clientTs)
    return {"ok": True}


# ------------------------------------------------------------------- agent
class AgentIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = []


@router.post("/agent")
def agent(body: AgentIn, request: Request):
    p = _participant(request)
    if not C.MODES[p["mode"]]["assistant"]:
        raise HTTPException(403, "this study has no assistant")
    if p["status"] != "pre_done":
        raise HTTPException(409, "the assistant is available during the allocation step only")
    with studydb.connect() as db:
        turns = db.value("SELECT COUNT(*) AS n FROM agent_turns WHERE participant_id=?", (p["id"],))
    if turns >= p["max_turns"]:
        raise HTTPException(429, "message limit reached")
    w = _wallet(p["id"], p["wallet_start"])
    history = [{"role": h.get("role"), "content": str(h.get("content", ""))[:4000]}
               for h in body.history[-12:] if h.get("role") in ("user", "assistant")]

    def gen():
        t0 = time.time()
        rec = {"engine": None, "model": None, "text": [], "steps": [], "shown": [], "blocks": [], "error": None}
        try:
            for ev in assistant.run(p["id"], p["lang"], p["wallet_start"], w["remaining"], body.message, history):
                if ev["type"] == "start":
                    rec["engine"], rec["model"] = ev["engine"], ev["model"]
                elif ev["type"] == "step":
                    rec["steps"].append({"tool": ev["tool"], "input": ev["input"]})
                elif ev["type"] == "text":
                    rec["text"].append(ev["text"])
                elif ev["type"] == "error":
                    rec["error"] = ev["message"]
                elif ev["type"] == "ui":
                    b = ev["block"]
                    rec["blocks"].append(b["kind"] + ("(auto)" if ev.get("auto") else ""))
                    cs = b.get("campaigns") or ([b["campaign"]] if "campaign" in b else [i["campaign"] for i in b.get("items", [])])
                    rec["shown"] += [c["id"] for c in cs]
                    for g in b.get("alternatives") or []:
                        rec["shown"] += [c["id"] for c in g["campaigns"]]
                yield f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
        finally:
            with studydb.connect() as db:
                db.execute(
                    """INSERT INTO agent_turns (participant_id,turn_index,user_message,assistant_text,steps,shown_campaigns,
                       blocks,engine,model,prompt_version,latency_ms,error,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (p["id"], turns + 1, body.message, "\n\n".join(rec["text"]), json.dumps(rec["steps"], ensure_ascii=False),
                     json.dumps(list(dict.fromkeys(rec["shown"]))), json.dumps(rec["blocks"]), rec["engine"], rec["model"],
                     assistant.PROMPT_VERSION, int((time.time() - t0) * 1000), rec["error"], _now()))

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------- finish/withdraw
@router.post("/finish")
def finish(request: Request):
    p = _participant(request)
    if p["status"] != "pre_done":
        raise HTTPException(409, f"cannot finish from status {p['status']}")
    w = _wallet(p["id"], p["wallet_start"])
    if not w["items"]:
        raise HTTPException(400, "allocate to at least one campaign first")
    nxt = "finished" if p["post_survey"] else "completed"
    with studydb.connect() as db:
        db.execute(f"UPDATE participants SET status='{nxt}', finished_at=?"
                   + (", completed_at=?" if nxt == "completed" else "") + " WHERE id=?",
                   (_now(), _now(), p["id"]) if nxt == "completed" else (_now(), p["id"]))
    _log(p["id"], "finish", payload={"allocated": w["allocated"], "remaining": w["remaining"], "n": len(w["items"])})
    return {"ok": True}


@router.post("/withdraw")
def withdraw(request: Request, response: Response):
    """Participant stops and asks for their data to be removed."""
    p = _participant(request)
    with studydb.connect() as db:
        for t in ("survey_responses", "allocations", "study_events", "agent_turns"):
            db.execute(f"DELETE FROM {t} WHERE participant_id=?", (p["id"],))
        db.execute("UPDATE participants SET status='withdrawn', nickname='', user_agent=NULL WHERE id=?", (p["id"],))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


# ----------------------------------------------------------------- preview
def _end_preview_run(request: Request) -> str | None:
    """Delete the current browser's preview run, if it has one. Returns its study id."""
    pid = request.cookies.get(COOKIE)
    if not pid:
        return None
    with studydb.connect() as db:
        row = db.one("SELECT study_id, is_preview FROM participants WHERE id=?", (pid,))
        if row and row["is_preview"]:
            _delete_participant(db, pid)
            return row["study_id"]
    return None


@router.post("/preview/restart")
def preview_restart(request: Request, response: Response):
    sid = _preview_study(request)
    if not sid:
        raise HTTPException(403, "not in preview mode")
    _end_preview_run(request)
    response.delete_cookie(COOKIE, path="/")
    return {"url": f"/s/{sid}"}


@router.post("/preview/exit")
def preview_exit(request: Request, response: Response):
    _end_preview_run(request)
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie(PREVIEW_COOKIE, path="/")
    return {"url": "/admin"}


# ------------------------------------------------------------------- admin
def _admin(request: Request) -> None:
    token = os.environ.get("STUDY_ADMIN_TOKEN")
    given = request.headers.get("x-admin-token") or request.query_params.get("token")
    if not token or not given or not secrets.compare_digest(token, given):
        raise HTTPException(403, "admin token required (set STUDY_ADMIN_TOKEN)")


# Design fields are frozen once a study has participants, so everyone in a
# study saw the same protocol. Name, notes and status stay editable.
DESIGN_FIELDS = ("mode", "wallet", "max_turns", "pre_survey", "post_survey")


class StudyIn(BaseModel):
    id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{2,39}$")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    mode: str | None = Field(default=None, pattern="^(assistant|assistant_browse|browse)$")
    wallet: float | None = Field(default=None, ge=10, le=1_000_000)
    maxTurns: int | None = Field(default=None, ge=1, le=200)
    preSurvey: bool | None = None
    postSurvey: bool | None = None
    status: str | None = Field(default=None, pattern="^(draft|open|closed)$")
    notes: str | None = Field(default=None, max_length=2000)


def _study_admin(r: dict, counts: dict) -> dict:
    return {"id": r["id"], "name": r["name"], "mode": r["mode"], "wallet": r["wallet"], "maxTurns": r["max_turns"],
            "preSurvey": bool(r["pre_survey"]), "postSurvey": bool(r["post_survey"]), "status": r["status"],
            "notes": r["notes"] or "", "createdAt": r["created_at"], "updatedAt": r["updated_at"],
            "participants": counts, "locked": sum(counts.values()) > 0,
            "consentVersion": C.consent_for(r["mode"], r["wallet"])["version"]}


def _counts(db, study_id: str) -> dict:
    """Real participants only: preview runs neither count nor lock a study."""
    return {r["status"]: r["n"] for r in db.all(
        "SELECT status, COUNT(*) AS n FROM participants WHERE study_id=? AND is_preview=0 GROUP BY status",
        (study_id,))}


@router.get("/admin/studies")
def admin_studies(request: Request):
    _admin(request)
    with studydb.connect() as db:
        rows = db.all("SELECT * FROM studies ORDER BY created_at DESC")
        out = [_study_admin(r, _counts(db, r["id"])) for r in rows]
    return {"studies": out, "modes": C.MODES, "engines": assistant.available_engines()}


@router.post("/admin/studies")
def admin_create_study(body: StudyIn, request: Request):
    _admin(request)
    sid = body.id or f"s{secrets.token_hex(3)}"
    now = _now()
    with studydb.connect() as db:
        if db.one("SELECT id FROM studies WHERE id=?", (sid,)):
            raise HTTPException(409, f"a study with id '{sid}' already exists")
        db.execute("""INSERT INTO studies (id,name,mode,wallet,max_turns,pre_survey,post_survey,status,notes,created_at,updated_at)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                   (sid, body.name or sid, body.mode or "assistant", body.wallet or C.DEFAULT_WALLET,
                    body.maxTurns or C.DEFAULT_MAX_TURNS, int(body.preSurvey is not False), int(body.postSurvey is not False),
                    body.status or "draft", body.notes or "", now, now))
        return _study_admin(db.one("SELECT * FROM studies WHERE id=?", (sid,)), {})


@router.patch("/admin/studies/{study_id}")
def admin_update_study(study_id: str, body: StudyIn, request: Request):
    _admin(request)
    changes = {"name": body.name, "mode": body.mode, "wallet": body.wallet, "max_turns": body.maxTurns,
               "pre_survey": None if body.preSurvey is None else int(body.preSurvey),
               "post_survey": None if body.postSurvey is None else int(body.postSurvey),
               "status": body.status, "notes": body.notes}
    changes = {k: v for k, v in changes.items() if v is not None}
    with studydb.connect() as db:
        cur = db.one("SELECT * FROM studies WHERE id=?", (study_id,))
        if not cur:
            raise HTTPException(404, "study not found")
        counts = _counts(db, study_id)
        frozen = [k for k in DESIGN_FIELDS if k in changes and changes[k] != cur[k]]
        if frozen and sum(counts.values()):
            raise HTTPException(409, "this study already has participants, so its design is locked "
                                     f"({', '.join(frozen)}). Create a new study instead.")
        if changes:
            sets = ", ".join(f"{k}=?" for k in changes)
            db.execute(f"UPDATE studies SET {sets}, updated_at=? WHERE id=?", (*changes.values(), _now(), study_id))
        return _study_admin(db.one("SELECT * FROM studies WHERE id=?", (study_id,)), counts)


@router.post("/admin/studies/{study_id}/preview")
def admin_preview(study_id: str, request: Request, response: Response):
    """Put this browser in preview mode for a study (drafts included)."""
    _admin(request)
    if not _study(study_id):
        raise HTTPException(404, "study not found")
    _end_preview_run(request)                   # a previous preview run in this browser
    response.delete_cookie(COOKIE, path="/")    # never reuse a participant session for a preview
    response.set_cookie(PREVIEW_COOKIE, f"{study_id}.{_preview_sig(study_id)}", max_age=60 * 60 * 12,
                        **_cookie_kw(request))
    return {"url": f"/s/{study_id}"}


@router.delete("/admin/studies/{study_id}")
def admin_delete_study(study_id: str, request: Request):
    _admin(request)
    with studydb.connect() as db:
        if sum(_counts(db, study_id).values()):
            raise HTTPException(409, "this study has participants; close it instead of deleting it")
        for r in db.all("SELECT id FROM participants WHERE study_id=? AND is_preview=1", (study_id,)):
            _delete_participant(db, r["id"])
        db.execute("DELETE FROM studies WHERE id=?", (study_id,))
    return {"ok": True}


def _study_filter(study: str | None, alias: str = "p") -> tuple[str, tuple]:
    """Real participants only (preview runs are excluded), optionally one study."""
    where = f" WHERE {alias}.is_preview = 0"
    return (where + f" AND {alias}.study_id=?", (study,)) if study else (where, ())


@router.get("/admin/summary")
def admin_summary(request: Request, study: str | None = None):
    _admin(request)
    where, args = _study_filter(study)
    join = " JOIN participants p ON p.id = t.participant_id"
    with studydb.connect() as db:
        by_status = {r["status"]: r["n"] for r in db.all(
            f"SELECT p.status, COUNT(*) AS n FROM participants p{where} GROUP BY p.status", args)}
        turns = db.value(f"SELECT COUNT(*) AS n FROM agent_turns t{join}{where}", args)
        events = db.value(f"SELECT COUNT(*) AS n FROM study_events t{join}{where}", args)
        allocated = db.value(f"SELECT COALESCE(SUM(t.amount),0) AS s FROM allocations t{join}{where}", args)
        engines = {f'{r["engine"]} / {r["model"] or ""}': r["n"] for r in db.all(
            f"SELECT t.engine, t.model, COUNT(*) AS n FROM agent_turns t{join}{where} GROUP BY t.engine, t.model", args)}
        top = db.all(f"SELECT t.campaign_id, COUNT(*) AS n, SUM(t.amount) AS total FROM allocations t{join}{where} "
                     "GROUP BY t.campaign_id ORDER BY total DESC LIMIT 10", args)
    found = campaigns_by_id([t["campaign_id"] for t in top])
    return {
        "storage": "postgres" if studydb.IS_PG else "sqlite", "study": study,
        "participants": by_status, "agentTurns": turns, "events": events, "allocated": allocated, "engines": engines,
        "topCampaigns": [{"title_ar": found.get(t["campaign_id"], {}).get("titleAr", t["campaign_id"]),
                          "title_en": found.get(t["campaign_id"], {}).get("titleEn", t["campaign_id"]),
                          "n": t["n"], "total": t["total"]} for t in top],
    }


STUDY_EXPORTS = {
    "participants": "SELECT p.id, p.study_id, p.code, p.nickname, p.lang, p.condition AS mode, p.consent_version, "
                    "p.consented_at, p.status, p.wallet_start, p.agent_config, p.pre_done_at, p.finished_at, "
                    "p.completed_at FROM participants p{where} ORDER BY p.consented_at",
    "allocations": "SELECT t.participant_id, p.study_id, t.campaign_id, t.amount, t.source, t.created_at, t.updated_at "
                   "FROM allocations t JOIN participants p ON p.id = t.participant_id{where} "
                   "ORDER BY t.participant_id, t.created_at",
    "events": "SELECT t.id, t.participant_id, p.study_id, t.type, t.campaign_id, t.payload, t.client_ts, t.created_at "
              "FROM study_events t JOIN participants p ON p.id = t.participant_id{where} ORDER BY t.id",
    "agent_turns": "SELECT t.id, t.participant_id, p.study_id, t.turn_index, t.user_message, t.assistant_text, t.steps, "
                   "t.shown_campaigns, t.blocks, t.engine, t.model, t.prompt_version, t.latency_ms, t.error, t.created_at "
                   "FROM agent_turns t JOIN participants p ON p.id = t.participant_id{where} ORDER BY t.id",
}


@router.get("/admin/export/{name}.csv")
def export(name: str, request: Request, study: str | None = None):
    _admin(request)
    where, args = _study_filter(study)
    buf = io.StringIO()
    w = csv.writer(buf)
    if name == "surveys":
        # one row per participant and phase, one column per question (all study designs)
        qids = C.all_question_ids()
        w.writerow(["participant_id", "study_id", "mode", "phase", "created_at"] + qids)
        with studydb.connect() as db:
            rows = db.all("SELECT t.participant_id, p.study_id, p.condition AS mode, t.phase, t.answers, t.created_at "
                          f"FROM survey_responses t JOIN participants p ON p.id = t.participant_id{where} "
                          "ORDER BY t.participant_id, t.phase", args)
        for r in rows:
            a = json.loads(r["answers"])
            w.writerow([r["participant_id"], r["study_id"], r["mode"], r["phase"], r["created_at"]] +
                       ["|".join(map(str, v)) if isinstance(v, list) else ("" if v is None else v)
                        for v in (a.get(q) for q in qids)])
    elif name == "studies":
        with studydb.connect() as db:
            cols, rows = db.columns("SELECT id, name, mode, wallet, max_turns, pre_survey, post_survey, status, notes, "
                                    "created_at, updated_at FROM studies ORDER BY created_at")
        w.writerow(cols); w.writerows(rows)
    elif name == "campaigns":
        conn = connect()
        cur = conn.execute("SELECT id, title_ar, title_en, category_id, charity_id, region, goal_amount, raised_amount, "
                           "unit_cost, is_zakat, is_waqf FROM campaigns ORDER BY id")
        w.writerow([d[0] for d in cur.description]); w.writerows(cur.fetchall())
        conn.close()
    elif name in STUDY_EXPORTS:
        with studydb.connect() as db:
            cols, rows = db.columns(STUDY_EXPORTS[name].replace("{where}", where), args)
        if name == "allocations":           # add the campaign's category for convenience
            cats = {k: v["categoryId"] for k, v in campaigns_by_id([r[2] for r in rows]).items()}
            cols = cols[:3] + ["category_id"] + cols[3:]
            rows = [r[:3] + (cats.get(r[2], ""),) + r[3:] for r in rows]
        w.writerow(cols); w.writerows(rows)
    else:
        raise HTTPException(404, "unknown export; choose from "
                                 f"{sorted([*STUDY_EXPORTS, 'surveys', 'studies', 'campaigns'])}")
    fname = f"{name}{'_' + study if study else ''}.csv"
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})
