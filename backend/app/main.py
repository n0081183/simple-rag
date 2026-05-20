"""FastAPI entrypoint — API + static Next.js export."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import health, kb, requirements, settings as settings_api
from app.config import get_settings
from app.infra.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title="Cortex Workbench",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(requirements.router, prefix="/api")
app.include_router(kb.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")

# Static frontend (after `make build` → frontend/out)
FRONTEND_OUT = Path(__file__).resolve().parents[2] / "frontend" / "out"


@app.get("/api/version")
def api_version():
    return {"version": __version__}


if FRONTEND_OUT.is_dir():
    app.mount("/_next", StaticFiles(directory=FRONTEND_OUT / "_next"), name="next-static")
    assets = FRONTEND_OUT / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve Next.js export; fallback to index.html for client routes."""
        if full_path.startswith("api"):
            return {"detail": "Not found"}
        candidate = FRONTEND_OUT / full_path
        if candidate.is_dir():
            index_in_dir = candidate / "index.html"
            if index_in_dir.is_file():
                return FileResponse(index_in_dir)
        if candidate.is_file():
            return FileResponse(candidate)
        # Next.js static export: /settings → settings/index.html
        if not full_path.endswith("/"):
            nested = FRONTEND_OUT / full_path / "index.html"
            if nested.is_file():
                return FileResponse(nested)
        index = FRONTEND_OUT / "index.html"
        if index.is_file():
            return FileResponse(index)
        return {"detail": "Frontend not built. Run: make build"}
