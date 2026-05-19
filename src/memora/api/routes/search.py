"""Unified search API route."""

from __future__ import annotations

from fastapi import APIRouter, Query

from memora.api.app import get_app

router = APIRouter()


@router.get("/")
async def unified_search(
    query: str,
    scope: str = Query("all", pattern="^(all|memory|knowledge|prompt)$"),
    top_k: int = Query(10, le=50),
):
    """Search across memories, documents, and prompts."""
    app = get_app()
    results = await app.search.search(query, scope=scope, top_k=top_k)
    return [r.model_dump() for r in results]


@router.get("/stats")
async def get_stats():
    """Get knowledge base statistics."""
    app = get_app()
    mem = await app.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM memories")
    docs = await app.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM documents")
    chunks = await app.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM document_chunks")
    prompts = await app.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM prompts")
    return {
        "memories": mem["cnt"] if mem else 0,
        "documents": docs["cnt"] if docs else 0,
        "document_chunks": chunks["cnt"] if chunks else 0,
        "prompts": prompts["cnt"] if prompts else 0,
    }
