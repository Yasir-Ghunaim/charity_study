"""Feature store shared by every recommendation strategy.

Builds, and caches in memory:
  * R  — user x campaign implicit-feedback matrix, time-decayed
  * item-item cosine similarity from R            (collaborative signal)
  * TF-IDF over normalised Arabic text + item-item cosine (content signal)
  * recent popularity / velocity

Rebuilt on demand; cheap enough at this catalogue size (72 x 600) to refresh
after every write in development.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime

import numpy as np

from ..db import CAMPAIGN_SELECT, connect

NOW = datetime(2026, 9, 24)
HALF_LIFE_DAYS = 180.0

EVENT_WEIGHT = {"view": 0.5, "click": 1.0, "share": 2.0, "add_to_cart": 3.0, "donate": 0.0}

# ------------------------------------------------------------ Arabic text prep
_DIACRITICS = re.compile(r"[ؗ-ًؚ-ْٰـ]")
_NON_WORD = re.compile(r"[^ء-ي٠-٩a-zA-Z0-9\s]")

STOPWORDS = {
    "من", "في", "على", "إلى", "عن", "مع", "هذا", "هذه", "ذلك", "التي", "الذي",
    "ما", "لا", "أن", "إن", "كان", "قد", "هو", "هي", "و", "او", "أو", "ثم",
    "بعد", "قبل", "كل", "بين", "عند", "حتى", "لهم", "لها", "له", "بها", "به",
    "خلال", "ضمن", "غير", "دون", "بشكل", "بما", "لكي", "حيث", "التي", "الى",
}


def normalize_ar(text: str) -> str:
    text = _DIACRITICS.sub("", text)
    text = (text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
                .replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي"))
    return _NON_WORD.sub(" ", text)


def tokenize_ar(text: str) -> list[str]:
    out = []
    for tok in normalize_ar(text).split():
        if tok.startswith("ال") and len(tok) > 4:
            tok = tok[2:]
        if len(tok) > 1 and tok not in STOPWORDS:
            out.append(tok)
    return out


def _decay(ts: str, ref: datetime) -> float:
    days = (ref - datetime.fromisoformat(ts)).days
    return 0.5 ** (max(0, days) / HALF_LIFE_DAYS)


def _cosine_sim(M: np.ndarray) -> np.ndarray:
    """Column-wise cosine similarity of a (rows x items) matrix -> items x items."""
    norms = np.linalg.norm(M, axis=0)
    norms[norms == 0] = 1.0
    Mn = M / norms
    S = Mn.T @ Mn
    np.fill_diagonal(S, 0.0)
    return S


class RecStore:
    def __init__(self, cutoff: str | None = None) -> None:
        # cutoff: ISO timestamp; only interactions strictly before it are used.
        # Used by the evaluation harness to prevent leakage from the test window.
        self.cutoff = cutoff
        # Every time-relative feature (decay, popularity windows) is measured
        # from `ref`, never from wall-clock NOW, so a cutoff store cannot see
        # the test window.
        self.ref = datetime.fromisoformat(cutoff) if cutoff else NOW
        self.refresh()

    # ------------------------------------------------------------------ build
    def refresh(self) -> None:
        conn = connect()
        cur = conn.cursor()
        where = " WHERE created_at < ?" if self.cutoff else ""
        args = (self.cutoff,) if self.cutoff else ()

        rows = cur.execute(CAMPAIGN_SELECT + " ORDER BY c.id").fetchall()
        self.campaigns = {r["id"]: dict(r) for r in rows}
        self.items = [r["id"] for r in rows]
        self.iidx = {c: i for i, c in enumerate(self.items)}
        n_items = len(self.items)

        users = [r[0] for r in cur.execute("SELECT id FROM users ORDER BY id")]
        self.users = users
        self.uidx = {u: i for i, u in enumerate(users)}
        n_users = len(users)

        # ---- interaction matrix
        R = np.zeros((n_users, n_items), dtype=np.float32)
        self.user_donations: dict[str, list[dict]] = {}
        for d in cur.execute(
                "SELECT user_id,campaign_id,amount,kind,created_at,is_recurring,source "
                "FROM donations" + where, args):
            ui, ii = self.uidx.get(d["user_id"]), self.iidx.get(d["campaign_id"])
            if ui is None or ii is None:
                continue
            # confidence grows with amount but sub-linearly, and decays with age
            R[ui, ii] += (5.0 + math.log1p(d["amount"]) * 0.8) * _decay(d["created_at"], self.ref)
            self.user_donations.setdefault(d["user_id"], []).append(dict(d))

        for e in cur.execute(
                "SELECT user_id,campaign_id,type,created_at FROM events" + where, args):
            w = EVENT_WEIGHT.get(e["type"], 0.0)
            if not w or not e["campaign_id"]:
                continue
            ui, ii = self.uidx.get(e["user_id"]), self.iidx.get(e["campaign_id"])
            if ui is None or ii is None:
                continue
            R[ui, ii] += w * _decay(e["created_at"], self.ref)
        self.R = R

        # ---- collaborative item-item similarity (BM25-ish column damping so
        #      blockbuster campaigns don't dominate every neighbourhood)
        col = R.sum(axis=0)
        damp = 1.0 / np.sqrt(np.maximum(col, 1.0))
        self.item_sim_cf = _cosine_sim(R * damp)

        # ---- content TF-IDF
        docs = []
        for cid in self.items:
            c = self.campaigns[cid]
            tags = " ".join(json.loads(c["tags"]))
            docs.append(tokenize_ar(
                f'{c["title_ar"]} {c["title_ar"]} {tags} {tags} '
                f'{c["category_name_ar"]} {c["category_name_ar"]} {c["description_ar"]}'))
        vocab: dict[str, int] = {}
        for d in docs:
            for t in d:
                vocab.setdefault(t, len(vocab))
        self.vocab = vocab
        tf = np.zeros((n_items, len(vocab)), dtype=np.float32)
        for i, d in enumerate(docs):
            for t in d:
                tf[i, vocab[t]] += 1.0
        df = (tf > 0).sum(axis=0)
        idf = np.log((1 + n_items) / (1 + df)) + 1.0
        tfidf = np.log1p(tf) * idf
        nrm = np.linalg.norm(tfidf, axis=1, keepdims=True)
        nrm[nrm == 0] = 1.0
        self.tfidf = tfidf / nrm
        self.item_sim_content = self.tfidf @ self.tfidf.T
        np.fill_diagonal(self.item_sim_content, 0.0)

        # ---- popularity: 90-day donor count, and velocity vs prior 90 days
        self.pop = np.zeros(n_items, dtype=np.float32)
        self.velocity = np.zeros(n_items, dtype=np.float32)
        recent = cur.execute(
            """SELECT campaign_id, COUNT(DISTINCT user_id) n FROM donations
               WHERE created_at >= date(?, '-90 day') AND created_at < ?
               GROUP BY 1""", (self.ref.isoformat(), self.ref.isoformat())).fetchall()
        prior = dict(cur.execute(
            """SELECT campaign_id, COUNT(DISTINCT user_id) FROM donations
               WHERE created_at >= date(?, '-180 day') AND created_at < date(?, '-90 day')
               GROUP BY 1""", (self.ref.isoformat(), self.ref.isoformat())).fetchall())
        for r in recent:
            i = self.iidx.get(r["campaign_id"])
            if i is None:
                continue
            self.pop[i] = r["n"]
            self.velocity[i] = r["n"] / max(1.0, prior.get(r["campaign_id"], 0) + 1)
        if self.pop.max() > 0:
            self.pop = self.pop / self.pop.max()

        self.built_at = datetime.utcnow().isoformat()
        conn.close()

    # --------------------------------------------------------------- helpers
    def user_vector(self, user_id: str) -> np.ndarray | None:
        i = self.uidx.get(user_id)
        return None if i is None else self.R[i]

    def content_profile(self, user_id: str) -> np.ndarray | None:
        """Weighted centroid of the TF-IDF vectors of what the donor supported."""
        v = self.user_vector(user_id)
        if v is None or v.sum() == 0:
            return None
        p = v @ self.tfidf
        n = np.linalg.norm(p)
        return None if n == 0 else p / n

    def donated_items(self, user_id: str) -> set[str]:
        return {d["campaign_id"] for d in self.user_donations.get(user_id, [])}

    def stats(self) -> dict:
        return {
            "users": len(self.users), "campaigns": len(self.items),
            "vocab": len(self.vocab), "builtAt": self.built_at,
            "density": float((self.R > 0).mean()),
        }


_store: RecStore | None = None


def get_store(force: bool = False) -> RecStore:
    global _store
    if _store is None or force:
        _store = RecStore()
    return _store
