"""RAG engine — Protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from memora.models.document import Document, DocumentChunk


@runtime_checkable
class RAGEngine(Protocol):
    """Interface for document ingestion and semantic retrieval."""

    async def ingest(self, path_or_url: str) -> Document:
        """Ingest a document: load → chunk → embed → store."""
        ...

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Semantic search over document chunks."""
        ...

    async def list_documents(self, limit: int = 50) -> list[Document]:
        """List ingested documents."""
        ...

    async def get_document(self, document_id: str) -> Document | None:
        """Get document metadata by ID."""
        ...

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        ...
