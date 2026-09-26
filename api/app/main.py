"""Ehsan-like donation platform — API.

Owns the SQLite database, the recommender and the agent. The Next.js frontend
is a pure consumer of these endpoints.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .db import connect, init_db                       # noqa: E402
from .routers import catalog, recs, users              # noqa: E402
from .study.router import router as study_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect(); init_db(conn); conn.close()
    n = 0
    conn = connect()
    try:
        n = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    finally:
        conn.close()
    if n == 0:
        from .seed.generate import build
        print("empty database — seeding…")
        print(build())
    from .rec.store import get_store
    get_store(force=True)                 # warm the matrices before first request
    from . import studydb
    print("study data:", studydb.init())
    from .search import status as search_status
    print("search:", search_status())     # embeds the catalogue once (cached on disk)
    yield


app = FastAPI(title="Ehsan Recommendation API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(catalog.router, prefix="/api", tags=["catalog"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(recs.router, prefix="/api", tags=["recommendations"])
app.include_router(study_router, prefix="/api")


@app.get("/api/health")
def health():
    from .rec.store import get_store
    return {"ok": True, "agentLlm": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "store": get_store().stats()}
