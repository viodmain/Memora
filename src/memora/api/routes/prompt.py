"""Prompt API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from memora.api.app import get_app

router = APIRouter()


class SavePromptRequest(BaseModel):
    name: str
    content: str
    description: str = ""
    variables: list[str] | None = None
    tags: list[str] | None = None


class ScoreRequest(BaseModel):
    score: float


@router.post("/")
async def save_prompt(req: SavePromptRequest):
    """Save a prompt (creates new version if name exists)."""
    app = get_app()
    result = await app.prompt.save(
        name=req.name,
        content=req.content,
        description=req.description,
        variables=req.variables,
        tags=req.tags,
    )
    return result.model_dump()


@router.get("/")
async def list_prompts(tag: str | None = None):
    """List prompts."""
    app = get_app()
    results = await app.prompt.list(tag=tag)
    return [r.model_dump() for r in results]


@router.get("/{name}")
async def get_prompt(name: str, version: int | None = None):
    """Get a prompt and its specified version (default: latest)."""
    app = get_app()
    try:
        prompt, ver = await app.prompt.get(name, version)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"prompt": prompt.model_dump(), "version": ver.model_dump()}


@router.post("/{name}/versions/{version}/score")
async def score_prompt(name: str, version: int, req: ScoreRequest):
    """Score a prompt version (1-5)."""
    app = get_app()
    try:
        await app.prompt.score(name, version, req.score)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.get("/{name}/compare")
async def compare_versions(name: str, v1: int, v2: int):
    """Compare two prompt versions."""
    app = get_app()
    try:
        result = await app.prompt.compare(name, v1, v2)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


@router.post("/{name}/optimize")
async def optimize_prompt(name: str, feedback: str = ""):
    """Generate optimization suggestions."""
    app = get_app()
    try:
        result = await app.prompt.optimize(name, feedback)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"suggestion": result}


@router.delete("/{name}")
async def delete_prompt(name: str):
    """Delete a prompt and all versions."""
    app = get_app()
    ok = await app.prompt.delete(name)
    if not ok:
        raise HTTPException(404, "Prompt not found")
    return {"ok": True}
