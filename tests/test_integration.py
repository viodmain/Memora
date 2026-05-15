"""Integration tests — end-to-end flows without API mocking."""

import pytest
import pytest_asyncio
from pathlib import Path

from memora.storage import create_storage
from memora.memory.engine import MemoryEngineImpl
from memora.rag.engine import RAGEngineImpl
from memora.prompt.engine import PromptEngineImpl
from memora.search.service import SearchServiceImpl
from memora.models.memory import Memory, MemoryType
from memora.llm import ExtractedMemory


# ── Stub LLM ─────────────────────────────────────────────────

class StubLLM:
    def __init__(self):
        self._dim = 8
        self._extract_result: list[ExtractedMemory] = []

    def set_extract_result(self, items: list[ExtractedMemory]):
        self._extract_result = items

    async def chat(self, messages, temperature=0.7):
        return '{"title": "Test", "summary": "Summary", "key_points": ["a"]}'

    async def extract_memories(self, messages):
        return list(self._extract_result)

    async def embed(self, text):
        vec = [0.0] * self._dim
        for i, ch in enumerate(text[:self._dim]):
            vec[i] = (ord(ch) % 100) / 100.0
        return vec

    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]


# ── Fixture ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def full_system(tmp_path):
    """Full system with all engines wired together."""
    storage = await create_storage(
        str(tmp_path / "test.db"),
        str(tmp_path / "chroma"),
    )
    llm = StubLLM()
    memory = MemoryEngineImpl(storage, llm)
    rag = RAGEngineImpl(storage, llm, chunk_size=200)
    prompt = PromptEngineImpl(storage, llm)
    search = SearchServiceImpl(memory, rag, prompt)

    yield {
        "storage": storage,
        "llm": llm,
        "memory": memory,
        "rag": rag,
        "prompt": prompt,
        "search": search,
    }
    await storage.close()


# ── Tests ────────────────────────────────────────────────────

class TestMemoryLifecycle:
    @pytest.mark.asyncio
    async def test_save_recall_delete(self, full_system):
        mem = full_system["memory"]

        # Save
        m = Memory(content="User likes Go", memory_type=MemoryType.PREFERENCE, source="test")
        await mem.save(m)

        # Recall
        results = await mem.recall("Go programming")
        assert len(results) == 1
        assert results[0].content == "User likes Go"

        # Delete
        ok = await mem.delete(m.id)
        assert ok is True
        results = await mem.recall("Go programming")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_extract_and_dedup(self, full_system):
        mem = full_system["memory"]
        llm = full_system["llm"]

        llm.set_extract_result([
            ExtractedMemory(content="User prefers Python", memory_type="preference", confidence=0.9),
        ])

        # First extraction
        result1 = await mem.extract_from_messages([{"role": "user", "content": "I like Python"}])
        assert len(result1) == 1

        # Duplicate extraction
        result2 = await mem.extract_from_messages([{"role": "user", "content": "I like Python"}])
        assert len(result2) == 0  # Deduped


class TestRAGLifecycle:
    @pytest.mark.asyncio
    async def test_ingest_and_search(self, full_system, tmp_path):
        rag = full_system["rag"]

        # Create test file
        md = tmp_path / "test.md"
        md.write_text("# Title\n\nThis is about Python programming.\n\n## Usage\n\nUse it for AI.")

        # Ingest
        doc = await rag.ingest(str(md))
        assert doc.chunk_count > 0

        # Search (stub embedding is not semantic, just verify results returned)
        results = await rag.search("Python programming")
        assert len(results) > 0
        assert all(r.content for r in results)

    @pytest.mark.asyncio
    async def test_delete_document(self, full_system, tmp_path):
        rag = full_system["rag"]

        md = tmp_path / "test.md"
        md.write_text("# Test\n\nContent here.")

        doc = await rag.ingest(str(md))
        ok = await rag.delete_document(doc.id)
        assert ok is True

        results = await rag.search("Content")
        assert len(results) == 0


class TestPromptLifecycle:
    @pytest.mark.asyncio
    async def test_versioning_and_scoring(self, full_system):
        p = full_system["prompt"]

        # Create v1
        await p.save("test", "v1 content")
        _, v1 = await p.get("test", version=1)
        assert v1.version == 1

        # Create v2
        await p.save("test", "v2 content")
        _, v2 = await p.get("test", version=2)
        assert v2.version == 2

        # Score
        await p.score("test", 1, 3.0)
        await p.score("test", 2, 4.5)

        # Compare
        diff = await p.compare("test", 1, 2)
        assert diff["content_changed"] is True
        assert diff["score_diff"] == 1.5


class TestUnifiedSearch:
    @pytest.mark.asyncio
    async def test_search_across_engines(self, full_system, tmp_path):
        mem = full_system["memory"]
        rag = full_system["rag"]
        search = full_system["search"]

        # Add memory
        await mem.save(Memory(content="Python is great", memory_type=MemoryType.FACT, source="test"))

        # Add document
        md = tmp_path / "guide.md"
        md.write_text("# Guide\n\nLearn Python step by step.")
        await rag.ingest(str(md))

        # Unified search
        results = await search.search("Python", scope="all")
        assert len(results) > 0
        sources = {r.source_type for r in results}
        assert "memory" in sources or "document" in sources
