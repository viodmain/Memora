"""ChromaDB vector storage implementation."""

from dataclasses import dataclass, field
from typing import Sequence

import chromadb


@dataclass
class VectorRecord:
    """A vector record to insert or update."""
    id: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)


@dataclass
class VectorSearchResult:
    """A single result from a vector similarity search."""
    id: str
    score: float
    metadata: dict


class VectorStore:
    """ChromaDB-backed vector storage for semantic search."""

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

    async def upsert(
        self,
        collection: str,
        records: Sequence[VectorRecord],
    ) -> None:
        """Insert or update vector records in a collection."""
        if not records:
            return
        col = self._get_collection(collection)
        col.upsert(
            ids=[r.id for r in records],
            embeddings=[r.embedding for r in records],
            metadatas=[r.metadata for r in records],
        )

    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors in a collection.

        Args:
            collection: Collection name ("memories", "documents", "prompts").
            query_embedding: The query vector.
            top_k: Maximum number of results.
            where: Optional metadata filter (ChromaDB where-clause).

        Returns:
            List of results sorted by similarity (lower distance = better).
        """
        col = self._get_collection(collection)
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        result = col.query(**kwargs)

        results = []
        if result["ids"] and result["ids"][0]:
            ids = result["ids"][0]
            distances = result["distances"][0] if result["distances"] else [0.0] * len(ids)
            metadatas = result["metadatas"][0] if result["metadatas"] else [{}] * len(ids)
            for id_, dist, meta in zip(ids, distances, metadatas):
                results.append(VectorSearchResult(id=id_, score=1.0 - dist, metadata=meta or {}))

        return results

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
