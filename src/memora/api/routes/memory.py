"""Memory API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from memora.api.app import get_app
from memora.models.memory import Memory, MemoryType

router = APIRouter()


class SaveMemoryRequest(BaseModel):
    content: str
    memory_type: str = "fact"
    source: str = "api"


class ExtractRequest(BaseModel):
    messages: list[dict]


@router.post("/save")
async def save_memory(req: SaveMemoryRequest):
    """Save a single memory."""
    app = get_app()
    memory = Memory(
        content=req.content,
        memory_type=MemoryType(req.memory_type),
        source=req.source,
    )
    result = await app.memory.save(memory)
    return result.model_dump()


@router.get("/recall")
async def recall(
    query: str,
    top_k: int = Query(5, le=50),
    memory_type: str | None = None,
):
    """Semantic search over memories."""
    app = get_app()
    mt = MemoryType(memory_type) if memory_type else None
    results = await app.memory.recall(query, top_k=top_k, memory_type=mt)
    return [r.model_dump() for r in results]


@router.post("/extract")
async def extract(req: ExtractRequest):
    """Extract memories from conversation messages."""
    app = get_app()
    results = await app.memory.extract_from_messages(req.messages)
    return [r.model_dump() for r in results]


@router.get("/")
async def list_memories(
    memory_type: str | None = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
):
    """List memories with optional filters."""
    app = get_app()
    mt = MemoryType(memory_type) if memory_type else None
    results = await app.memory.list(memory_type=mt, limit=limit, offset=offset)
    return [r.model_dump() for r in results]


@router.get("/{memory_id}")
async def get_memory(memory_id: str):
    """Get a specific memory by ID."""
    app = get_app()
    result = await app.memory.get(memory_id)
    if not result:
        raise HTTPException(404, "Memory not found")
    return result.model_dump()


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory."""
    app = get_app()
    ok = await app.memory.delete(memory_id)
    if not ok:
        raise HTTPException(404, "Memory not found")
    return {"ok": True}
