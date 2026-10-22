from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRouter

from sloth_organizer.database import init_db

# ---------------------------------------------------------------------------
# Stub routers (replaced by real implementations in Sub-Tasks 3–5)
# ---------------------------------------------------------------------------

scan_router = APIRouter(prefix="/scan", tags=["scan"])
plan_router = APIRouter(prefix="/plans", tags=["plan"])
apply_router = APIRouter(prefix="/plans", tags=["apply"])
lm_router = APIRouter(prefix="/lm-studio", tags=["lm-studio"])


@scan_router.get("/health")
async def scan_health() -> dict:
    return {"status": "ok", "router": "scan"}


@plan_router.get("/health")
async def plan_health() -> dict:
    return {"status": "ok", "router": "plan"}


@lm_router.get("/status")
async def lm_studio_status() -> dict:
    return {"connected": False, "model": None}


# ---------------------------------------------------------------------------
# Lifespan — stub ready for DB init in Sub-Task 2
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sloth Organizer",
    version="0.1.0",
    lifespan=lifespan,
)

# API routers under /api
app.include_router(scan_router, prefix="/api")
app.include_router(plan_router, prefix="/api")
app.include_router(apply_router, prefix="/api")
app.include_router(lm_router, prefix="/api")

# Static files — SPA fallback (must be mounted last)
_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)

app.mount(
    "/",
    StaticFiles(directory=str(_static_dir), html=True),
    name="static",
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    uvicorn.run(
        "sloth_organizer.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    run()
