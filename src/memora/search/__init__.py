"""Unified search service — Protocol definition."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from memora.models.search import SearchResult


@runtime_checkable
class SearchService(Protocol):
    """Interface for unified search across memory, documents, and prompts."""

    async def search(
        self,
        query: str,
        scope: Literal["all", "memory", "knowledge", "prompt"] = "all",
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Search across engines, merge and rank results."""
        ...
