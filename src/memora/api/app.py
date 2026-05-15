"""FastAPI application — REST API entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from memora.app import App, create_app


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


# Register routes
from memora.api.routes import memory, knowledge, prompt, search  # noqa: E402

app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(prompt.router, prefix="/api/prompt", tags=["prompt"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


@app.get("/")
async def root():
    return {"name": "Memora", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
