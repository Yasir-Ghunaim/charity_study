"""Campaign search: Arabic-aware keyword matching + semantic embeddings.

  lexical   Arabic normalisation (أإآ→ا, ة→ه, ى→ي, no tashkeel), clitic
            stripping (ال/وال/بال/لل…), prefix matching, field weights
            (title > tags, category > description), idf so rare words count more.
  semantic  multilingual embeddings from a local Ollama model (default bge-m3):
            «عطشى» can find «سقيا», «مرضى الكلى» can find «الغسيل الكلوي».

Campaign vectors are cached in data/embeddings_<model>.json keyed by a hash of
the text, so only the query is embedded per search. If the embedding model is
unavailable, search degrades to lexical-only instead of failing.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time

import httpx
import numpy as np

from .db import DB_PATH, connect
from .seed.info import CATEGORY_TERMS, CATEGORY_TERMS_EN

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")

W_SEM, W_LEX = 0.65, 0.35     # blend when both signals are available
# Cosine scales differ a lot between queries, so semantic scores are placed on
# each query's own scale: 0 = the median campaign, 1 = the best match.
SEM_GATE = 0.55                # below this (on that scale) a campaign needs a keyword hit to qualify
FIELD_WEIGHTS = {"title": 3.0, "tags": 2.0, "category": 2.0, "description": 1.0}

# ------------------------------------------------------------------ lexical
_TASHKEEL = re.compile(r"[ؐ-ًؚ-ْٰـ]")
_NON_WORD = re.compile(r"[^ء-ي0-9a-zA-Z\s]")
_CLITICS = ("وال", "بال", "فال", "كال", "لل", "ال")
_STOP = {"من", "في", "على", "الى", "عن", "مع", "او", "ان", "هذا", "هذه", "التي", "الذي", "ما",
         "لا", "كل", "بين", "عند", "اريد", "ابي", "ابغى", "ابحث", "عن", "لي", "حملات", "حمله",
         "فرص", "فرصه", "تبرع", "التبرع", "اتبرع", "دعم", "مشروع", "مشاريع", "ريال",
         "i", "want", "to", "the", "a", "an", "for", "of", "and", "with", "who", "in", "on", "my", "me", "help",
         "donate", "give", "support", "some", "campaign", "campaigns", "people", "are", "is", "that", "have"}


def normalize(text: str) -> str:
    text = _TASHKEEL.sub("", text)
    text = (text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
                .replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي"))
    return _NON_WORD.sub(" ", text).lower()


def tokens(text: str) -> list[str]:
    out = []
    for t in normalize(text).split():
        if t in _STOP:
            continue
        for c in _CLITICS:
            if t.startswith(c) and len(t) - len(c) >= 3:
                t = t[len(c):]
                break
        if len(t) >= 2 and t not in _STOP:
            out.append(t)
    return out


def _match(q: str, d: str) -> float:
    """1 for an exact token match, 0.8 for a shared 4+ letter prefix (يتيم ~ يتيمه), else 0."""
    if q == d:
        return 1.0
    if min(len(q), len(d)) >= 4 and (d.startswith(q) or q.startswith(d)):
        return 0.8
    return 0.0


class _Index:
    RETRY_SECONDS = 300          # how often to retry semantic search when the model is unavailable

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.built_for: str | None = None
        self.last_try = 0.0
        self.sem_ok = False

    def build(self) -> None:
        conn = connect()
        rows = conn.execute(
            "SELECT c.id, c.title_ar, c.title_en, c.tags, c.description_ar, c.description_en, c.unit_ar, c.unit_en, "
            "cat.name_ar cat, cat.name_en cat_en, c.category_id "
            "FROM campaigns c JOIN categories cat ON cat.id=c.category_id").fetchall()
        conn.close()
        self.ids = [r["id"] for r in rows]
        self.fields = {r["id"]: {
            "title": tokens(f'{r["title_ar"]} {r["title_en"]}'),
            "tags": tokens(" ".join(json.loads(r["tags"]))),
            "category": tokens(f'{r["cat"]} {r["cat_en"]} {CATEGORY_TERMS.get(r["category_id"], "")} '
                               f'{CATEGORY_TERMS_EN.get(r["category_id"], "")}'),
            "description": tokens(f'{r["description_ar"]} {r["unit_ar"] or ""} {r["description_en"]} {r["unit_en"] or ""}'),
        } for r in rows}
        self.docs = {r["id"]: f'{r["title_ar"]}. {r["cat"]}. {"، ".join(json.loads(r["tags"]))}. '
                              f'{r["description_ar"]} {r["unit_ar"] or ""}. '
                              f'{CATEGORY_TERMS.get(r["category_id"], "")}\n'
                              f'{r["title_en"]}. {r["cat_en"]}. {r["description_en"]} {r["unit_en"] or ""}. '
                              f'{CATEGORY_TERMS_EN.get(r["category_id"], "")}' for r in rows}
        self.vecs: dict[str, np.ndarray] = {}
        self.sem_ok = self._load_embeddings()
        self.built_for = ",".join(self.ids)

    # ------------------------------------------------------------ semantic
    def _embed(self, texts: list[str]) -> list[list[float]] | None:
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/embed", json={"model": EMBED_MODEL, "input": texts},
                           timeout=httpx.Timeout(60, connect=2))
            if r.status_code != 200:
                return None
            return r.json().get("embeddings")
        except Exception:
            return None

    def _load_embeddings(self) -> bool:
        path = DB_PATH.parent / f"embeddings_{EMBED_MODEL.replace(':', '_').replace('/', '_')}.json"
        cache = {}
        if path.exists():
            try:
                cache = json.loads(path.read_text())
            except ValueError:
                cache = {}
        todo = []
        for cid, text in self.docs.items():
            h = hashlib.sha1(text.encode()).hexdigest()
            if cache.get(cid, {}).get("h") == h:
                self.vecs[cid] = np.asarray(cache[cid]["v"], dtype=np.float32)
            else:
                todo.append((cid, h, text))
        for i in range(0, len(todo), 16):
            batch = todo[i:i + 16]
            embs = self._embed([t for _, _, t in batch])
            if not embs:
                return bool(self.vecs) and not todo      # partial caches are not trusted
            for (cid, h, _), v in zip(batch, embs):
                cache[cid] = {"h": h, "v": v}
                self.vecs[cid] = np.asarray(v, dtype=np.float32)
        if todo:
            path.write_text(json.dumps(cache))
        for cid, v in self.vecs.items():
            n = float(np.linalg.norm(v))
            self.vecs[cid] = v / n if n else v
        return len(self.vecs) == len(self.ids)

    def ensure(self) -> None:
        with self.lock:
            stale = not self.sem_ok and time.time() - self.last_try > self.RETRY_SECONDS
            if self.built_for is None or stale:
                self.last_try = time.time()
                self.build()


_index = _Index()


def status() -> dict:
    _index.ensure()
    return {"semantic": _index.sem_ok, "model": EMBED_MODEL if _index.sem_ok else None,
            "campaigns": len(_index.ids)}


def rank(query: str, candidates: list[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
    """Return [(campaign_id, score)] best first, only for campaigns that plausibly match."""
    _index.ensure()
    pool = [c for c in (candidates if candidates is not None else _index.ids) if c in _index.fields]
    if not pool or not query.strip():
        return []

    # lexical
    q_toks = list(dict.fromkeys(tokens(query)))
    n = len(_index.ids)
    lex = {}
    for cid in pool:
        f = _index.fields[cid]
        s = 0.0
        for q in q_toks:
            df = sum(1 for d in _index.ids
                     if any(_match(q, t) for fld in _index.fields[d].values() for t in fld))
            idf = math.log((n + 1) / (df + 0.5))
            best = max((FIELD_WEIGHTS[name] * max((_match(q, t) for t in toks), default=0.0)
                        for name, toks in f.items()), default=0.0)
            s += best * idf
        lex[cid] = s
    top_lex = max(lex.values(), default=0.0)

    # semantic
    sem = {}
    if _index.sem_ok:
        qv = _index._embed([query])
        if not qv:                       # model went away: keywords only until the next retry window
            _index.sem_ok = False
            _index.last_try = time.time()
        if qv:
            v = np.asarray(qv[0], dtype=np.float32)
            v = v / (np.linalg.norm(v) or 1.0)
            sem = {cid: float(_index.vecs[cid] @ v) for cid in pool}

    if sem:
        vals = np.array(list(sem.values()))
        med, top = float(np.median(vals)), float(vals.max())
        span = (top - med) or 1.0
    scored = []
    for cid in pool:
        l = lex[cid] / top_lex if top_lex else 0.0
        if sem:
            s_n = max(0.0, (sem[cid] - med) / span)
            if l == 0 and s_n < SEM_GATE:
                continue
            score = W_SEM * s_n + W_LEX * l
        else:
            if l == 0:
                continue
            score = l
        scored.append((cid, score))
    scored.sort(key=lambda x: -x[1])
    if scored:                                   # drop the long tail of weak matches
        cut = scored[0][1] * 0.45
        scored = [x for x in scored if x[1] >= cut]
    return scored[:limit]
