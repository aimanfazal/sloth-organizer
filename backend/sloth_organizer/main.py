from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sloth_organizer.database import init_db
from sloth_organizer.routers.scan import router as scan_router, ws_router
from sloth_organizer.routers.plan import router as plan_router
from sloth_organizer.routers.lm_studio import router as lm_router
from sloth_organizer.routers.apply import router as apply_router


# ---------------------------------------------------------------------------
# Lifespan
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

# API routers
app.include_router(scan_router, prefix="/api")
app.include_router(plan_router, prefix="/api")
app.include_router(lm_router, prefix="/api")
app.include_router(apply_router, prefix="/api")

# WebSocket router (no /api prefix)
app.include_router(ws_router)

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
