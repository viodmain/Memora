"""Unified search service — implementation."""

from __future__ import annotations

import asyncio

from memora.models.search import SearchResult
from memora.memory import MemoryEngine
from memora.rag import RAGEngine
from memora.prompt import PromptEngine


class SearchServiceImpl:
    """Aggregate search results from memory, document, and prompt engines."""

    def __init__(
        self,
        memory_engine: MemoryEngine,
        rag_engine: RAGEngine,
        prompt_engine: PromptEngine,
    ) -> None:
        self._memory = memory_engine
        self._rag = rag_engine
        self._prompt = prompt_engine

    async def search(
        self,
        query: str,
        scope: str = "all",
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Search across engines in parallel, merge by relevance.

        Args:
            query: Search text.
            scope: "all", "memory", "knowledge", or "prompt".
            top_k: Total max results.

        Returns:
            Merged results sorted by relevance_score DESC.
        """
        tasks = []
        per_engine_k = max(top_k, 5)

        if scope in ("all", "memory"):
            tasks.append(self._search_memory(query, per_engine_k))
        if scope in ("all", "knowledge"):
            tasks.append(self._search_knowledge(query, per_engine_k))
        if scope in ("all", "prompt"):
            tasks.append(self._search_prompts(query, per_engine_k))

        if not tasks:
            return []

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        merged: list[SearchResult] = []
        for result in results_list:
            if isinstance(result, Exception):
                continue  # Skip failed engines
            merged.extend(result)

        merged.sort(key=lambda r: r.relevance_score, reverse=True)
        return merged[:top_k]

    async def _search_memory(self, query: str, top_k: int) -> list[SearchResult]:
        memories = await self._memory.recall(query, top_k=top_k)
        return [
            SearchResult(
                content=m.content,
                source_type="memory",
                source_id=m.id,
                relevance_score=1.0,  # Vector search already ranked
                metadata={"type": m.memory_type.value, "tags": m.tags},
            )
            for m in memories
        ]

    async def _search_knowledge(self, query: str, top_k: int) -> list[SearchResult]:
        chunks = await self._rag.search(query, top_k=top_k)
        return [
            SearchResult(
                content=c.content,
                source_type="document",
                source_id=c.document_id,
                relevance_score=1.0,
                metadata={"chunk_id": c.id, "chunk_index": c.chunk_index},
            )
            for c in chunks
        ]

    async def _search_prompts(self, query: str, top_k: int) -> list[SearchResult]:
        # Prompt search: filter by name/description/tags containing query keywords
        prompts = await self._prompt.list()
        results: list[SearchResult] = []
        query_lower = query.lower()

        for p in prompts:
            if (
                query_lower in p.name.lower()
                or query_lower in p.description.lower()
                or any(query_lower in t.lower() for t in p.tags)
            ):
                results.append(SearchResult(
                    content=f"{p.name}: {p.description}",
                    source_type="prompt",
                    source_id=p.id,
                    relevance_score=0.5,  # Lower than vector search
                    metadata={"name": p.name, "tags": p.tags},
                ))

        return results[:top_k]
