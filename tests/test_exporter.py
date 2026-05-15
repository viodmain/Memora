"""Tests for data export."""

import json
import csv
import pytest
import pytest_asyncio
from pathlib import Path

from memora.storage import create_storage
from memora.storage.exporter import (
    export_memories_json,
    export_memories_csv,
    export_documents_json,
    export_all_json,
)


@pytest_asyncio.fixture
async def storage_with_data(tmp_path):
    """Storage with sample data for export testing."""
    storage = await create_storage(
        str(tmp_path / "test.db"),
        str(tmp_path / "chroma"),
    )

    # Insert sample memories
    for i in range(3):
        await storage.db.execute(
            "INSERT INTO memories (id, content, memory_type, source, confidence, tags, access_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"mem_{i}", f"Memory {i}", "fact", "test", 1.0, "", i, "2026-01-01", "2026-01-01"),
        )

    # Insert sample document
    await storage.db.execute(
        "INSERT INTO documents (id, title, source_path, source_type, file_type, chunk_count, ingested_at, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("doc_1", "Test Doc", "/tmp/test.md", "file", "md", 3, "2026-01-01", "{}"),
    )

    yield storage
    await storage.close()


class TestExportMemoriesJSON:
    @pytest.mark.asyncio
    async def test_export_json(self, storage_with_data, tmp_path):
        path = str(tmp_path / "memories.json")
        count = await export_memories_json(storage_with_data.db, path)

        assert count == 3
        data = json.loads(Path(path).read_text())
        assert len(data) == 3
        assert data[0]["content"] == "Memory 0"

    @pytest.mark.asyncio
    async def test_export_json_creates_dirs(self, storage_with_data, tmp_path):
        path = str(tmp_path / "subdir" / "memories.json")
        count = await export_memories_json(storage_with_data.db, path)
        assert count == 3


class TestExportMemoriesCSV:
    @pytest.mark.asyncio
    async def test_export_csv(self, storage_with_data, tmp_path):
        path = str(tmp_path / "memories.csv")
        count = await export_memories_csv(storage_with_data.db, path)

        assert count == 3
        with open(path, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 4  # header + 3 rows
        assert rows[0][1] == "content"


class TestExportDocumentsJSON:
    @pytest.mark.asyncio
    async def test_export_documents(self, storage_with_data, tmp_path):
        path = str(tmp_path / "docs.json")
        count = await export_documents_json(storage_with_data.db, path)

        assert count == 1
        data = json.loads(Path(path).read_text())
        assert data[0]["title"] == "Test Doc"


class TestExportAllJSON:
    @pytest.mark.asyncio
    async def test_export_all(self, storage_with_data, tmp_path):
        path = str(tmp_path / "export.json")
        counts = await export_all_json(storage_with_data.db, path)

        assert counts["memories"] == 3
        assert counts["documents"] == 1
        assert counts["prompts"] == 0

        data = json.loads(Path(path).read_text())
        assert "exported_at" in data
        assert len(data["memories"]) == 3
