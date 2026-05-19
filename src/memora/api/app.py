"""FastAPI application — REST API entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from memora.app import App, create_app

STATIC_DIR = Path(__file__).parent.parent / "static"


_app_instance: App | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global _app_instance
    _app_instance = await create_app()
    yield
    if _app_instance:
        await _app_instance.shutdown()
        _app_instance = None


def get_app() -> App:
    """Get the running App instance."""
    if _app_instance is None:
        raise RuntimeError("App not initialized")
    return _app_instance


app = FastAPI(
    title="Memora API",
    description="Personal knowledge base API",
    version="0.1.0",
    lifespan=lifespan,
)


# Register API routes
from memora.api.routes import memory, knowledge, prompt, search  # noqa: E402

app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(prompt.router, prefix="/api/prompt", tags=["prompt"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


@app.get("/api")
async def api_root():
    return {"name": "Memora API", "version": "0.1.0", "status": "running"}


@app.get("/api/status")
async def api_status():
    return {"name": "Memora API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve Vue frontend if built files exist
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve Vue SPA — all non-API routes return index.html."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
