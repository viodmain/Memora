"""ChromaDB vector storage implementation.

Supports two modes:
1. Text mode (default): ChromaDB handles embedding internally via its built-in
   ONNX embedding function (all-MiniLM-L6-v2). No external API needed.
2. Manual mode: caller provides pre-computed embeddings.
"""

from dataclasses import dataclass, field
from typing import Sequence

import chromadb


@dataclass
class VectorRecord:
    """A vector record to insert or update (manual embedding mode)."""
    id: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)


@dataclass
class TextRecord:
    """A text record to insert or update (text mode — ChromaDB embeds internally)."""
    id: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class VectorSearchResult:
    """A single result from a vector similarity search."""
    id: str
    score: float
    metadata: dict


class VectorStore:
    """ChromaDB-backed vector storage for semantic search.

    Collections: "memories", "documents", "prompts".
    Uses ChromaDB's built-in ONNX embedding by default (no API key needed).
    """

    COLLECTIONS = ("memories", "documents", "prompts")

    def __init__(self, persist_directory: str = "data/chroma") -> None:
        self._persist_directory = persist_directory
        self._client: chromadb.ClientAPI | None = None
        self._collections: dict[str, chromadb.Collection] = {}

    async def initialize(self) -> None:
        """Create ChromaDB client and ensure all collections exist."""
        self._client = chromadb.PersistentClient(path=self._persist_directory)
        for name in self.COLLECTIONS:
            self._collections[name] = self._client.get_or_create_collection(name)

    async def close(self) -> None:
        """Release resources (ChromaDB PersistentClient auto-persists)."""
        self._collections.clear()
        self._client = None

    def _get_collection(self, name: str) -> chromadb.Collection:
        """Get a collection by name; raises if not found."""
        if name not in self._collections:
            raise ValueError(f"Unknown collection: {name}. Available: {self.COLLECTIONS}")
        return self._collections[name]

    # ── Text mode (preferred) ─────────────────────────────────

    async def upsert_texts(
        self,
        collection: str,
        records: Sequence[TextRecord],
    ) -> None:
        """Insert or update text records. ChromaDB handles embedding internally."""
        if not records:
            return
        col = self._get_collection(collection)
        metadatas = [r.metadata if r.metadata else None for r in records]
        col.upsert(
            ids=[r.id for r in records],
            documents=[r.content for r in records],
            metadatas=metadatas,
        )

    async def search_text(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        """Search by text query. ChromaDB handles query embedding internally."""
        col = self._get_collection(collection)
        kwargs: dict = {
            "query_texts": [query],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        result = col.query(**kwargs)
        return self._parse_query_result(result)

    # ── Manual embedding mode ─────────────────────────────────

    async def upsert(
        self,
        collection: str,
        records: Sequence[VectorRecord],
    ) -> None:
        """Insert or update vector records with pre-computed embeddings."""
        if not records:
            return
        col = self._get_collection(collection)
        metadatas = [r.metadata if r.metadata else None for r in records]
        col.upsert(
            ids=[r.id for r in records],
            embeddings=[r.embedding for r in records],
            metadatas=metadatas,
        )

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        """Search by pre-computed query embedding."""
        col = self._get_collection(collection)
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        result = col.query(**kwargs)
        return self._parse_query_result(result)

    # ── Common ────────────────────────────────────────────────

    async def delete(self, collection: str, ids: Sequence[str]) -> None:
        """Delete records by ID from a collection."""
        if not ids:
            return
        col = self._get_collection(collection)
        col.delete(ids=list(ids))

    async def count(self, collection: str) -> int:
        """Return the number of records in a collection."""
        col = self._get_collection(collection)
        return col.count()

    @staticmethod
    def _parse_query_result(result: dict) -> list[VectorSearchResult]:
        """Parse ChromaDB query result into VectorSearchResult list."""
        results = []
        if result["ids"] and result["ids"][0]:
            ids = result["ids"][0]
            distances = result["distances"][0] if result["distances"] else [0.0] * len(ids)
            metadatas = result["metadatas"][0] if result["metadatas"] else [{}] * len(ids)
            for id_, dist, meta in zip(ids, distances, metadatas):
                results.append(VectorSearchResult(id=id_, score=1.0 - dist, metadata=meta or {}))
        return results
