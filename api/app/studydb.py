"""Storage for participant data, kept apart from the campaign catalogue.

  DATABASE_URL=postgresql://…  → Postgres (e.g. Neon); survives restarts on free hosts
  unset                        → local SQLite file data/study.db (development)

The catalogue (campaigns, charities…) stays in data/ehsan.db and is rebuilt
identically from the seed at every start, so free hosts that wipe their disk
lose nothing. Only this module holds data that must persist.

SQL is written once with `?` placeholders and ON CONFLICT upserts, which both
engines accept; `?` is translated to `%s` for Postgres.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "study.db"


def _ddl(pg: bool) -> str:
    serial = "BIGSERIAL PRIMARY KEY" if pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    real = "DOUBLE PRECISION" if pg else "REAL"
    return f"""
CREATE TABLE IF NOT EXISTS studies (
    id           TEXT PRIMARY KEY,          -- short id used in the participant link /s/<id>
    name         TEXT NOT NULL,             -- internal name, admin only
    mode         TEXT NOT NULL,             -- assistant | browse | assistant_browse
    wallet       {real} NOT NULL,
    max_turns    INTEGER NOT NULL,
    pre_survey   INTEGER NOT NULL DEFAULT 1,
    post_survey  INTEGER NOT NULL DEFAULT 1,
    status       TEXT NOT NULL DEFAULT 'draft',   -- draft | open | closed
    notes        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS participants (
    id              TEXT PRIMARY KEY,
    study_id        TEXT REFERENCES studies(id),
    code            TEXT NOT NULL UNIQUE,
    nickname        TEXT NOT NULL,
    lang            TEXT NOT NULL DEFAULT 'ar',
    condition       TEXT NOT NULL DEFAULT 'agent',
    consent_version TEXT NOT NULL,
    consented_at    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'consented',
    wallet_start    {real} NOT NULL,
    agent_config    TEXT,
    pre_done_at     TEXT,
    finished_at     TEXT,
    completed_at    TEXT,
    user_agent      TEXT,
    is_preview      INTEGER NOT NULL DEFAULT 0     -- admin preview runs: never counted as study data
);
CREATE TABLE IF NOT EXISTS survey_responses (
    id             {serial},
    participant_id TEXT NOT NULL REFERENCES participants(id),
    phase          TEXT NOT NULL,
    answers        TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    UNIQUE (participant_id, phase)
);
CREATE TABLE IF NOT EXISTS allocations (
    participant_id TEXT NOT NULL REFERENCES participants(id),
    campaign_id    TEXT NOT NULL,
    amount         {real} NOT NULL,
    source         TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    PRIMARY KEY (participant_id, campaign_id)
);
CREATE TABLE IF NOT EXISTS study_events (
    id             {serial},
    participant_id TEXT NOT NULL,
    type           TEXT NOT NULL,
    campaign_id    TEXT,
    payload        TEXT,
    client_ts      TEXT,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_turns (
    id              {serial},
    participant_id  TEXT NOT NULL,
    turn_index      INTEGER NOT NULL,
    user_message    TEXT NOT NULL,
    assistant_text  TEXT,
    steps           TEXT,
    shown_campaigns TEXT,
    blocks          TEXT,
    engine          TEXT,
    model           TEXT,
    prompt_version  TEXT,
    latency_ms      INTEGER,
    error           TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_part_study ON participants(study_id);
CREATE INDEX IF NOT EXISTS idx_sev_p   ON study_events(participant_id);
CREATE INDEX IF NOT EXISTS idx_turns_p ON agent_turns(participant_id);
"""


def _sql(q: str) -> str:
    return q.replace("?", "%s") if IS_PG else q


@contextmanager
def connect():
    """A connection whose rows are dicts; commits on success, rolls back on error."""
    if IS_PG:
        import psycopg
        from psycopg.rows import dict_row
        # prepare_threshold=None: no server-side prepared statements, which keeps
        # the connection safe behind poolers such as Neon's (PgBouncer).
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=15, prepare_threshold=None)
    else:
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = lambda cur, row: {d[0]: v for d, v in zip(cur.description, row)}
        conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield _Conn(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class _Conn:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, q: str, params=()):
        cur = self.raw.cursor()
        cur.execute(_sql(q), tuple(params))
        return cur

    def all(self, q: str, params=()) -> list[dict]:
        return list(self.execute(q, params).fetchall())

    def one(self, q: str, params=()) -> dict | None:
        return self.execute(q, params).fetchone()

    def value(self, q: str, params=()):
        row = self.one(q, params)
        return None if row is None else next(iter(row.values()))

    def columns(self, q: str, params=()) -> tuple[list[str], list[tuple]]:
        cur = self.execute(q, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return cols, [tuple(r[c] for c in cols) for r in rows]


def _columns(c: "_Conn", table: str) -> set[str]:
    if IS_PG:
        return {r["column_name"] for r in c.all(
            "SELECT column_name FROM information_schema.columns WHERE table_name=?", (table,))}
    return {r["name"] for r in c.all(f"PRAGMA table_info({table})")}


def init() -> str:
    with connect() as c:
        # databases created before multi-study support: add the column first,
        # so the index in the DDL below can be created
        if "participants" in _tables(c):
            cols = _columns(c, "participants")
            if "study_id" not in cols:
                c.execute("ALTER TABLE participants ADD COLUMN study_id TEXT")
            if "is_preview" not in cols:
                c.execute("ALTER TABLE participants ADD COLUMN is_preview INTEGER NOT NULL DEFAULT 0")
        if IS_PG:
            c.execute(_ddl(True))
        else:
            c.raw.executescript(_ddl(False))
    return "postgres" if IS_PG else f"sqlite ({SQLITE_PATH.name})"


def _tables(c: "_Conn") -> set[str]:
    if IS_PG:
        return {r["table_name"] for r in c.all(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()")}
    return {r["name"] for r in c.all("SELECT name FROM sqlite_master WHERE type='table'")}
