"""Offline evaluation: temporal hold-out over the simulated donation history.

Protocol
  * validation: train < VAL_CUT,  score gifts in [VAL_CUT, TEST_CUT)   -> tune here
  * test:       train < TEST_CUT, score gifts in [TEST_CUT, end)       -> report here
Every time-relative feature is anchored to the training cutoff (see
RecStore.ref), and no strategy ever reads `users.segment`.

Metrics are split because half of all gifts are repeats to a campaign the donor
already supports: `recall_repeat` rewards reminding, `recall_new` rewards
discovery. A strategy that only excludes history can never score on repeats.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime

from ..db import connect
from . import strategies as S
from .store import RecStore

VAL_CUT = datetime(2026, 3, 24)
TEST_CUT = datetime(2026, 6, 24)
END = datetime(2026, 9, 25)


def _dcg(hits: list[int]) -> float:
    return sum(h / math.log2(i + 2) for i, h in enumerate(hits))


def _window(cut: datetime, end: datetime, min_train: int):
    conn = connect()
    truth: dict[str, dict[str, float]] = defaultdict(dict)
    for r in conn.execute(
            "SELECT user_id, campaign_id, SUM(amount) amt FROM donations "
            "WHERE created_at >= ? AND created_at < ? GROUP BY 1,2",
            (cut.isoformat(), end.isoformat())):
        truth[r["user_id"]][r["campaign_id"]] = r["amt"]
    history: dict[str, set[str]] = defaultdict(set)
    for r in conn.execute("SELECT user_id, campaign_id FROM donations WHERE created_at < ?",
                          (cut.isoformat(),)):
        history[r["user_id"]].add(r["campaign_id"])
    segments = dict(conn.execute("SELECT id, segment FROM users").fetchall())
    conn.close()
    users = sorted(u for u in truth if len(history.get(u, ())) >= min_train)
    return truth, history, segments, users


def score(fn, store: RecStore, cut: datetime, truth, history, users, k: int = 10,
          segments=None, **kw) -> dict:
    agg = defaultdict(float)
    n_rep = n_new = 0
    shown: set[str] = set()
    per_seg = defaultdict(lambda: [0, 0.0])
    for u in users:
        want = truth[u]
        out = fn(store, user_id=u, k=k, now=cut, **kw)
        ids = [r.campaign_id for r in out]
        shown.update(ids)
        hits = [1 if c in want else 0 for c in ids]
        ideal = _dcg([1] * min(len(want), k))
        ndcg = _dcg(hits) / ideal if ideal else 0.0
        agg["recall"] += sum(hits) / len(want)
        agg["ndcg"] += ndcg
        agg["mrr"] += next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
        agg["rev"] += sum(want[c] for c in ids if c in want)
        agg["rev_max"] += sum(want.values())
        rep = {c for c in want if c in history[u]}
        new = set(want) - rep
        if rep:
            n_rep += 1
            agg["recall_repeat"] += len(rep & set(ids)) / len(rep)
        if new:
            n_new += 1
            agg["recall_new"] += len(new & set(ids)) / len(new)
        if segments:
            per_seg[segments[u]][0] += 1
            per_seg[segments[u]][1] += ndcg
    n = len(users)
    res = {
        f"recall@{k}": agg["recall"] / n,
        f"ndcg@{k}": agg["ndcg"] / n,
        "mrr": agg["mrr"] / n,
        "recall_repeat": agg["recall_repeat"] / max(1, n_rep),
        "recall_new": agg["recall_new"] / max(1, n_new),
        "revenue_captured": agg["rev"] / max(1.0, agg["rev_max"]),
        "coverage": len(shown) / len(store.items),
    }
    res = {key: round(v, 4) for key, v in res.items()}
    if segments:
        res["ndcg_by_segment"] = {s: round(t / c, 4) for s, (c, t) in sorted(per_seg.items())}
    return res


def evaluate(k: int = 10, split: str = "test", min_train: int = 2) -> dict:
    cut, end = (VAL_CUT, TEST_CUT) if split == "val" else (TEST_CUT, END)
    truth, history, segments, users = _window(cut, end, min_train)
    store = RecStore(cutoff=cut.isoformat())
    results = {}
    for name in ("popularity", "content", "cf", "hybrid"):
        results[name] = score(S.STRATEGIES[name], store, cut, truth, history, users, k,
                              segments=segments if name == "hybrid" else None)
    seg = results["hybrid"].pop("ndcg_by_segment")
    return {"split": split, "cutoff": cut.isoformat(), "k": k, "eval_users": len(users),
            "test_pairs": sum(len(v) for v in truth.values()),
            "strategies": results, "hybrid_ndcg_by_segment": seg}


def _print(r: dict) -> None:
    print(f"[{r['split']}] cutoff={r['cutoff'][:10]}  users={r['eval_users']}  pairs={r['test_pairs']}\n")
    cols = [c for c in next(iter(r["strategies"].values()))]
    print(f"{'strategy':<12}" + "".join(f"{c:>18}" for c in cols))
    for name, m in r["strategies"].items():
        print(f"{name:<12}" + "".join(f"{m[c]:>18.4f}" for c in cols))
    print("\nhybrid NDCG by donor segment:")
    for s, v in r["hybrid_ndcg_by_segment"].items():
        print(f"  {s:<20} {v:.4f}")


if __name__ == "__main__":
    import sys
    _print(evaluate(split=sys.argv[1] if len(sys.argv) > 1 else "test"))
