"""Tests for Phase 3 enhanced features: decay, auto-organize, auth."""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from memora.memory.engine import MemoryEngineImpl
from memora.models.memory import Memory, MemoryType
from memora.storage import create_storage


# ── Stub LLM ─────────────────────────────────────────────────

class StubLLM:
    def __init__(self):
        self._dim = 8

    async def chat(self, messages, temperature=0.7):
        return "ok"

    async def extract_memories(self, messages):
        return []

    async def embed(self, text):
        vec = [0.0] * self._dim
        for i, ch in enumerate(text[:self._dim]):
            vec[i] = (ord(ch) % 100) / 100.0
        return vec

    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]


@pytest_asyncio.fixture
async def engine(tmp_path):
    storage = await create_storage(
        str(tmp_path / "test.db"),
        str(tmp_path / "chroma"),
    )
    llm = StubLLM()
    eng = MemoryEngineImpl(storage, llm)
    yield eng
    await storage.close()


# ── Memory Decay Tests ───────────────────────────────────────

class TestMemoryDecay:
    @pytest.mark.asyncio
    async def test_list_sort_by_relevance(self, engine):
        # Create memories with different access counts
        m1 = Memory(content="rarely accessed", memory_type=MemoryType.FACT, source="test")
        m2 = Memory(content="frequently accessed", memory_type=MemoryType.FACT, source="test")
        await engine.save(m1)
        await engine.save(m2)

        # Simulate access
        await engine.get(m2.id)
        await engine.get(m2.id)
        await engine.get(m2.id)

        results = await engine.list(sort_by="relevance")
        assert len(results) == 2
        # Frequently accessed should be first
        assert results[0].content == "frequently accessed"

    @pytest.mark.asyncio
    async def test_list_sort_default(self, engine):
        m1 = Memory(content="first", memory_type=MemoryType.FACT, source="test")
        m2 = Memory(content="second", memory_type=MemoryType.FACT, source="test")
        await engine.save(m1)
        await engine.save(m2)

        results = await engine.list(sort_by="created_at")
        assert results[0].content == "second"  # Most recent first


# ── Auto-organize Tests ─────────────────────────────────────

class TestAutoOrganize:
    @pytest.mark.asyncio
    async def test_remove_exact_duplicates(self, engine):
        await engine.save(Memory(content="duplicate content", memory_type=MemoryType.FACT, source="test"))
        await engine.save(Memory(content="duplicate content", memory_type=MemoryType.FACT, source="test"))
        await engine.save(Memory(content="unique content", memory_type=MemoryType.FACT, source="test"))

        result = await engine.auto_organize()
        assert result["duplicates_removed"] == 1

        remaining = await engine.list(limit=100)
        assert len(remaining) == 2

    @pytest.mark.asyncio
    async def test_remove_stale_memories(self, engine):
        # Create a memory with old created_at
        m = Memory(content="old memory", memory_type=MemoryType.FACT, source="test")
        await engine.save(m)

        # Backdate it to 60 days ago
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        await engine._storage.db.execute(
            "UPDATE memories SET created_at = ?, access_count = 0 WHERE id = ?",
            (old_date, m.id),
        )

        result = await engine.auto_organize()
        assert result["stale_removed"] == 1

        remaining = await engine.list(limit=100)
        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_keep_accessed_stale_memories(self, engine):
        # Old but accessed memory should NOT be removed
        m = Memory(content="used old memory", memory_type=MemoryType.FACT, source="test")
        await engine.save(m)
        await engine.get(m.id)  # Access it

        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        await engine._storage.db.execute(
            "UPDATE memories SET created_at = ? WHERE id = ?",
            (old_date, m.id),
        )

        result = await engine.auto_organize()
        assert result["stale_removed"] == 0


# ── API Key Auth Tests ───────────────────────────────────────

class TestAPIKeyAuth:
    def test_auth_disabled_by_default(self):
        from memora.api.auth import verify_api_key
        # No MEMORA_API_KEY set = auth disabled
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MEMORA_API_KEY", None)
            result = verify_api_key(None)
            assert result == ""

    def test_auth_rejects_missing_key(self):
        from memora.api.auth import verify_api_key
        with patch.dict(os.environ, {"MEMORA_API_KEY": "test-secret"}):
            with pytest.raises(Exception):
                verify_api_key(None)

    def test_auth_rejects_wrong_key(self):
        from memora.api.auth import verify_api_key
        with patch.dict(os.environ, {"MEMORA_API_KEY": "test-secret"}):
            with pytest.raises(Exception):
                verify_api_key("wrong-key")

    def test_auth_accepts_correct_key(self):
        from memora.api.auth import verify_api_key
        with patch.dict(os.environ, {"MEMORA_API_KEY": "test-secret"}):
            result = verify_api_key("test-secret")
            assert result == "test-secret"
