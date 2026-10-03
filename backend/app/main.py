import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai.provider import LLMError, get_provider
from app.ai.services import provider_name
from app.api import auth, stories, updates
from app.config import APP_NAME, get_settings
from app.db import engine, init_db


class _Ping(BaseModel):
    ok: bool


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, stories.router, updates.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True, "app": APP_NAME, "llm": provider_name(), "db": engine.dialect.name}


@app.get("/api/health/llm")
def health_llm():
    """Diagnostyka: jedno małe wywołanie LLM. Zwraca typ błędu (bez sekretów), jeśli się nie uda."""
    t0 = time.perf_counter()
    try:
        get_provider().complete_json(
            "health", "Odpowiedz w formacie json.", 'Zwróć {"ok": true}.', _Ping
        )
        return {"ok": True, "llm": provider_name(), "ms": round((time.perf_counter() - t0) * 1000)}
    except (LLMError, ValueError) as e:
        return {"ok": False, "llm": provider_name(), "error": str(e)}


# Lokalnie / w kontenerze: serwuj zbudowany frontend. Na Vercelu robi to CDN.
STATIC = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if STATIC.exists() and not os.environ.get("VERCEL"):
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = STATIC / path
        return FileResponse(f if path and f.is_file() else STATIC / "index.html")
