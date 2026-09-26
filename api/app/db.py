"""SQLite data layer. The API owns the database; the Next.js frontend never
touches it directly."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ehsan.db"

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS categories (
    id        TEXT PRIMARY KEY,
    name_ar   TEXT NOT NULL,
    name_en   TEXT NOT NULL,
    glyph     TEXT NOT NULL,
    hue       INTEGER NOT NULL,
    sort      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS campaigns (
    id                TEXT PRIMARY KEY,
    title_ar          TEXT NOT NULL,
    title_en          TEXT NOT NULL,
    description_ar    TEXT NOT NULL,
    description_en    TEXT NOT NULL DEFAULT '',
    category_id       TEXT NOT NULL REFERENCES categories(id),
    tags              TEXT NOT NULL DEFAULT '[]',
    goal_amount       REAL NOT NULL,
    raised_amount     REAL NOT NULL DEFAULT 0,
    beneficiaries     INTEGER NOT NULL DEFAULT 0,
    region            TEXT NOT NULL,
    charity           TEXT NOT NULL,
    charity_id        TEXT REFERENCES charities(id),
    unit_ar           TEXT,
    unit_en           TEXT,
    unit_cost         REAL,
    zakat_category    TEXT,
    is_zakat          INTEGER NOT NULL DEFAULT 0,
    is_waqf           INTEGER NOT NULL DEFAULT 0,
    min_donation      REAL NOT NULL DEFAULT 10,
    suggested_amounts TEXT NOT NULL DEFAULT '[]',
    created_at        TEXT NOT NULL,
    ends_at           TEXT,
    status            TEXT NOT NULL DEFAULT 'active',
    featured          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS charities (
    id               TEXT PRIMARY KEY,
    name_ar          TEXT NOT NULL,
    license_no       TEXT NOT NULL,
    founded_year     INTEGER NOT NULL,
    hq_region        TEXT NOT NULL,
    focus            TEXT NOT NULL DEFAULT '[]',
    description_ar   TEXT NOT NULL,
    name_en          TEXT NOT NULL DEFAULT '',
    description_en   TEXT NOT NULL DEFAULT '',
    governance_score INTEGER NOT NULL,   -- 0-100, synthetic
    overhead_pct     REAL NOT NULL,      -- share of spend on administration
    audited_year     INTEGER,            -- latest published audited statement
    beneficiaries_last_year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS campaign_updates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    text_ar     TEXT NOT NULL,
    text_en     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    name_ar    TEXT NOT NULL,
    email      TEXT UNIQUE,
    city       TEXT NOT NULL,
    segment    TEXT NOT NULL,          -- ground-truth archetype, for eval only
    language   TEXT NOT NULL DEFAULT 'ar',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS donations (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(id),
    campaign_id  TEXT NOT NULL REFERENCES campaigns(id),
    amount       REAL NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'sadaqah',  -- sadaqah | zakat | waqf
    is_recurring INTEGER NOT NULL DEFAULT 0,
    source       TEXT NOT NULL DEFAULT 'feed',     -- feed|search|category|agent|nudge
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    campaign_id TEXT,
    type        TEXT NOT NULL,   -- view|click|add_to_cart|share|search|donate
    session_id  TEXT,
    meta        TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
    amount      REAL NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(user_id, campaign_id)
);

CREATE INDEX IF NOT EXISTS idx_don_user     ON donations(user_id);
CREATE INDEX IF NOT EXISTS idx_don_campaign ON donations(campaign_id);
CREATE INDEX IF NOT EXISTS idx_don_time     ON donations(created_at);
CREATE INDEX IF NOT EXISTS idx_ev_user      ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_ev_campaign  ON events(campaign_id);
CREATE INDEX IF NOT EXISTS idx_camp_cat     ON campaigns(category_id);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


from .seed.en import REGIONS_EN as _REGIONS_EN, ZAKAT_CATEGORY_EN as _ZAKAT_EN  # noqa: E402


def row_to_campaign(r: sqlite3.Row) -> dict:
    """Shape a campaign row the way the frontend wants it."""
    goal = r["goal_amount"] or 0
    raised = r["raised_amount"] or 0
    pct = min(100, round(raised / goal * 100)) if goal else 0
    return {
        "id": r["id"],
        "titleAr": r["title_ar"],
        "titleEn": r["title_en"],
        "descriptionAr": r["description_ar"],
        "descriptionEn": r["description_en"],
        "categoryId": r["category_id"],
        "categoryNameAr": r["category_name_ar"] if "category_name_ar" in r.keys() else None,
        "categoryNameEn": r["category_name_en"] if "category_name_en" in r.keys() else None,
        "hue": r["hue"] if "hue" in r.keys() else 160,
        "glyph": r["glyph"] if "glyph" in r.keys() else "grid",
        "tags": json.loads(r["tags"]),
        "goalAmount": goal,
        "raisedAmount": raised,
        "remainingAmount": max(0, goal - raised),
        "progressPct": pct,
        "beneficiaries": r["beneficiaries"],
        "region": r["region"],
        "charity": r["charity"],
        "charityId": r["charity_id"],
        "unitAr": r["unit_ar"],
        "unitEn": r["unit_en"] if "unit_en" in r.keys() else None,
        "charityEn": r["charity_en"] if "charity_en" in r.keys() else None,
        "regionEn": _REGIONS_EN.get(r["region"], r["region"]),
        "zakatCategoryEn": _ZAKAT_EN.get(r["zakat_category"]) if r["zakat_category"] else None,
        "unitCost": r["unit_cost"],
        "zakatCategory": r["zakat_category"],
        "isZakat": bool(r["is_zakat"]),
        "isWaqf": bool(r["is_waqf"]),
        "minDonation": r["min_donation"],
        "suggestedAmounts": json.loads(r["suggested_amounts"]),
        "createdAt": r["created_at"],
        "endsAt": r["ends_at"],
        "status": r["status"],
        "featured": bool(r["featured"]),
        "nearComplete": pct >= 90,
    }


CAMPAIGN_SELECT = """
SELECT c.*, cat.name_ar AS category_name_ar, cat.name_en AS category_name_en,
       cat.hue AS hue, cat.glyph AS glyph, ch.name_en AS charity_en
FROM campaigns c JOIN categories cat ON cat.id = c.category_id
LEFT JOIN charities ch ON ch.id = c.charity_id
"""
