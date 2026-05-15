"""RAG engine — implementation."""

from __future__ import annotations

from datetime import datetime

from memora.models.document import Document, DocumentChunk
from memora.storage import Storage
from memora.storage.vector_store import VectorRecord
from memora.llm import LLMClient
from memora.rag.chunker import MarkdownChunker
from memora.rag.loaders import LoaderRegistry, create_default_registry


class RAGEngineImpl:
    """Concrete implementation of the RAGEngine Protocol.

    Pipeline: load file → chunk text → embed chunks → store in SQLite + ChromaDB.
    """

    def __init__(
        self,
        storage: Storage,
        llm: LLMClient,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        loaders: LoaderRegistry | None = None,
    ) -> None:
        self._storage = storage
        self._llm = llm
        self._chunker = MarkdownChunker(chunk_size, chunk_overlap)
        self._loaders = loaders or create_default_registry()

    async def ingest(self, path_or_url: str) -> Document:
        """Ingest a document: load → chunk → embed → store.

        Args:
            path_or_url: File path (supports .md, .txt, .py, etc.)

        Returns:
            Document metadata with chunk count.
        """
        # 1. Load
        loader = self._loaders.get_loader(path_or_url)
        result = await loader.load(path_or_url)

        # 2. Chunk
        chunks = self._chunker.split(result.content, result.metadata)
        if not chunks:
            raise ValueError(f"No content extracted from: {path_or_url}")

        # 3. Create document record
        doc = Document(
            title=result.metadata.get("title", path_or_url),
            source_path=result.metadata.get("source_path", path_or_url),
            source_type=result.metadata.get("source_type", "file"),
            file_type=result.metadata.get("file_type", "txt"),
            chunk_count=len(chunks),
            metadata=result.metadata,
        )

        # 4. Store document metadata
        await self._storage.db.execute(
            "INSERT INTO documents (id, title, source_path, source_type, file_type, chunk_count, ingested_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (doc.id, doc.title, doc.source_path, doc.source_type, doc.file_type,
             doc.chunk_count, doc.ingested_at.isoformat(), "{}"),
        )

        # 5. Embed and store chunks
        texts = [c.content for c in chunks]
        embeddings = await self._llm.embed_batch(texts)

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc.id}_{i}"
            # Store chunk metadata in SQLite
            await self._storage.db.execute(
                "INSERT INTO document_chunks (id, document_id, content, chunk_index, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (chunk_id, doc.id, chunk.content, i, str(chunk.metadata)),
            )
            # Store vector in ChromaDB
            await self._storage.vector.upsert("documents", [
                VectorRecord(
                    id=chunk_id,
                    embedding=embedding,
                    metadata={"document_id": doc.id, "heading": chunk.metadata.get("heading", "")},
                )
            ])

        return doc

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Semantic search over document chunks.

        Args:
            query: Search query text.
            top_k: Maximum results.
            document_id: Optional filter to a specific document.

        Returns:
            List of matching DocumentChunks, ordered by relevance.
        """
        query_embedding = await self._llm.embed(query)
        where = {"document_id": document_id} if document_id else None
        results = await self._storage.vector.search(
            "documents", query_embedding, top_k=top_k, where=where
        )

        chunks: list[DocumentChunk] = []
        for r in results:
            row = await self._storage.db.fetch_one(
                "SELECT * FROM document_chunks WHERE id = ?", (r.id,)
            )
            if row:
                chunks.append(DocumentChunk(
                    id=row["id"],
                    document_id=row["document_id"],
                    content=row["content"],
                    chunk_index=row["chunk_index"],
                ))
        return chunks

    async def list_documents(self, limit: int = 50) -> list[Document]:
        """List ingested documents ordered by ingestion time DESC."""
        rows = await self._storage.db.fetch_all(
            "SELECT * FROM documents ORDER BY ingested_at DESC LIMIT ?", (limit,)
        )
        return [self._row_to_document(r) for r in rows]

    async def get_document(self, document_id: str) -> Document | None:
        """Get document metadata by ID."""
        row = await self._storage.db.fetch_one(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        )
        if row is None:
            return None
        return self._row_to_document(row)

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks (SQLite cascade + ChromaDB)."""
        row = await self._storage.db.fetch_one(
            "SELECT id FROM documents WHERE id = ?", (document_id,)
        )
        if row is None:
            return False

        # Delete vectors from ChromaDB
        chunk_rows = await self._storage.db.fetch_all(
            "SELECT id FROM document_chunks WHERE document_id = ?", (document_id,)
        )
        chunk_ids = [r["id"] for r in chunk_rows]
        if chunk_ids:
            await self._storage.vector.delete("documents", chunk_ids)

        # Delete from SQLite (cascade deletes chunks)
        await self._storage.db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return True

    @staticmethod
    def _row_to_document(row: dict) -> Document:
        """Convert a SQLite row to a Document model."""
        return Document(
            id=row["id"],
            title=row["title"],
            source_path=row["source_path"],
            source_type=row["source_type"],
            file_type=row["file_type"],
            chunk_count=row["chunk_count"],
            ingested_at=datetime.fromisoformat(row["ingested_at"]),
        )
