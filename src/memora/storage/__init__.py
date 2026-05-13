"""Storage layer facade.

Provides a unified Storage object that engines use to access
both SQLite (structured data) and ChromaDB (vectors).
"""

from dataclasses import dataclass
from pathlib import Path

from .database import SQLiteStore
from .vector_store import VectorStore, VectorRecord, VectorSearchResult


@dataclass
class Storage:
    """Unified storage facade holding both backends."""
    db: SQLiteStore
    vector: VectorStore

    async def initialize(self) -> None:
        """Initialize both storage backends."""
        await self.db.initialize()
        await self.vector.initialize()

    async def close(self) -> None:
        """Close both storage backends."""
        await self.vector.close()
        await self.db.close()


async def create_storage(
    db_path: str = "data/memora.db",
    chroma_path: str = "data/chroma",
) -> Storage:
    """Factory: create and initialize a Storage instance.

    Ensures parent directories exist before opening connections.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(chroma_path).parent.mkdir(parents=True, exist_ok=True)

    storage = Storage(
        db=SQLiteStore(db_path),
        vector=VectorStore(chroma_path),
    )
    await storage.initialize()
    return storage
