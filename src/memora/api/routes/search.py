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
