"""Tests for storage layer (SQLite + ChromaDB)."""

import pytest
import pytest_asyncio

from memora.storage import Storage
from memora.storage.vector_store import VectorRecord


class TestSQLiteStore:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, storage: Storage):
        # schema_version table should exist and contain version 1
        row = await storage.db.fetch_one("SELECT version FROM schema_version")
        assert row is not None
        assert row["version"] == 1

    @pytest.mark.asyncio
    async def test_execute_and_fetch_one(self, storage: Storage):
        await storage.db.execute(
            "INSERT INTO memories (id, content, memory_type, source, confidence, tags, access_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("m1", "test content", "fact", "test", 1.0, "", 0, "2026-01-01", "2026-01-01"),
        )
        row = await storage.db.fetch_one("SELECT * FROM memories WHERE id = ?", ("m1",))
        assert row is not None
        assert row["content"] == "test content"
        assert row["memory_type"] == "fact"

    @pytest.mark.asyncio
    async def test_fetch_one_not_found(self, storage: Storage):
        row = await storage.db.fetch_one("SELECT * FROM memories WHERE id = ?", ("nonexistent",))
        assert row is None

    @pytest.mark.asyncio
    async def test_fetch_all(self, storage: Storage):
        for i in range(3):
            await storage.db.execute(
                "INSERT INTO memories (id, content, memory_type, source, confidence, tags, access_count, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"m{i}", f"content {i}", "fact", "test", 1.0, "", 0, "2026-01-01", "2026-01-01"),
            )
        rows = await storage.db.fetch_all("SELECT * FROM memories ORDER BY id")
        assert len(rows) == 3
        assert rows[0]["id"] == "m0"

    @pytest.mark.asyncio
    async def test_execute_many(self, storage: Storage):
        params = [
            (f"batch{i}", f"batch content {i}", "fact", "test", 1.0, "", 0, "2026-01-01", "2026-01-01")
            for i in range(5)
        ]
        await storage.db.execute_many(
            "INSERT INTO memories (id, content, memory_type, source, confidence, tags, access_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params,
        )
        rows = await storage.db.fetch_all("SELECT * FROM memories")
        assert len(rows) == 5

    @pytest.mark.asyncio
    async def test_cascade_delete(self, storage: Storage):
        # Insert document and chunk
        await storage.db.execute(
            "INSERT INTO documents (id, title, source_path, source_type, file_type, chunk_count, ingested_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("d1", "Test Doc", "/tmp/test.md", "file", "md", 1, "2026-01-01", "{}"),
        )
        await storage.db.execute(
            "INSERT INTO document_chunks (id, document_id, content, chunk_index, metadata) "
            "VALUES (?, ?, ?, ?, ?)",
            ("c1", "d1", "chunk text", 0, "{}"),
        )
        # Delete document should cascade to chunks
        await storage.db.execute("DELETE FROM documents WHERE id = ?", ("d1",))
        row = await storage.db.fetch_one("SELECT * FROM document_chunks WHERE id = ?", ("c1",))
        assert row is None

    @pytest.mark.asyncio
    async def test_prompt_unique_name(self, storage: Storage):
        await storage.db.execute(
            "INSERT INTO prompts (id, name, description, tags, latest_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("p1", "unique-prompt", "", "", 0, "2026-01-01"),
        )
        with pytest.raises(Exception):
            await storage.db.execute(
                "INSERT INTO prompts (id, name, description, tags, latest_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("p2", "unique-prompt", "", "", 0, "2026-01-01"),
            )


class TestVectorStore:
    @pytest.mark.asyncio
    async def test_upsert_and_search(self, storage: Storage):
        records = [
            VectorRecord(id="v1", embedding=[1.0, 0.0, 0.0], metadata={"type": "fact"}),
            VectorRecord(id="v2", embedding=[0.0, 1.0, 0.0], metadata={"type": "preference"}),
        ]
        await storage.vector.upsert("memories", records)

        results = await storage.vector.search("memories", [1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0].id == "v1"  # closest match

    @pytest.mark.asyncio
    async def test_search_with_filter(self, storage: Storage):
        await storage.vector.upsert("memories", [
            VectorRecord(id="f1", embedding=[1.0, 0.0], metadata={"type": "fact"}),
            VectorRecord(id="p1", embedding=[0.9, 0.1], metadata={"type": "preference"}),
        ])
        results = await storage.vector.search(
            "memories", [1.0, 0.0], top_k=5, where={"type": "fact"}
        )
        assert len(results) == 1
        assert results[0].id == "f1"

    @pytest.mark.asyncio
    async def test_delete(self, storage: Storage):
        await storage.vector.upsert("memories", [
            VectorRecord(id="del1", embedding=[0.5, 0.5], metadata={}),
        ])
        await storage.vector.delete("memories", ["del1"])
        count = await storage.vector.count("memories")
        assert count == 0

    @pytest.mark.asyncio
    async def test_count(self, storage: Storage):
        await storage.vector.upsert("memories", [
            VectorRecord(id="c1", embedding=[0.1, 0.2], metadata={}),
            VectorRecord(id="c2", embedding=[0.3, 0.4], metadata={}),
        ])
        assert await storage.vector.count("memories") == 2

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, storage: Storage):
        await storage.vector.upsert("memories", [
            VectorRecord(id="u1", embedding=[1.0, 0.0], metadata={"version": 1}),
        ])
        await storage.vector.upsert("memories", [
            VectorRecord(id="u1", embedding=[0.0, 1.0], metadata={"version": 2}),
        ])
        count = await storage.vector.count("memories")
        assert count == 1  # updated, not duplicated

    @pytest.mark.asyncio
    async def test_unknown_collection_raises(self, storage: Storage):
        with pytest.raises(ValueError, match="Unknown collection"):
            await storage.vector.upsert("nonexistent", [VectorRecord(id="x", embedding=[0.0], metadata={})])

    @pytest.mark.asyncio
    async def test_empty_upsert_is_noop(self, storage: Storage):
        await storage.vector.upsert("memories", [])
        assert await storage.vector.count("memories") == 0

    @pytest.mark.asyncio
    async def test_empty_delete_is_noop(self, storage: Storage):
        await storage.vector.delete("memories", [])  # should not raise
