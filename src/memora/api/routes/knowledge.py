"""Knowledge (RAG) API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from memora.api.app import get_app

router = APIRouter()


@router.get("/search")
async def search_knowledge(
    query: str,
    top_k: int = Query(5, le=50),
    document_id: str | None = None,
):
    """Search document chunks by semantic similarity."""
    app = get_app()
    results = await app.rag.search(query, top_k=top_k, document_id=document_id)
    return [r.model_dump() for r in results]


@router.post("/ingest")
async def ingest_document(path: str):
    """Ingest a document by file path."""
    app = get_app()
    try:
        doc = await app.rag.ingest(path)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return doc.model_dump()


@router.get("/documents")
async def list_documents(limit: int = Query(50, le=200)):
    """List ingested documents."""
    app = get_app()
    results = await app.rag.list_documents(limit=limit)
    return [r.model_dump() for r in results]


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get document metadata."""
    app = get_app()
    result = await app.rag.get_document(document_id)
    if not result:
        raise HTTPException(404, "Document not found")
    return result.model_dump()


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its chunks."""
    app = get_app()
    ok = await app.rag.delete_document(document_id)
    if not ok:
        raise HTTPException(404, "Document not found")
    return {"ok": True}
