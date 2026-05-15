"""Tests for SearchService and App container."""

import pytest
import pytest_asyncio

from memora.app import App, create_app
from memora.search import SearchService
from memora.search.service import SearchServiceImpl
from memora.models.search import SearchResult
from memora.memory.engine import MemoryEngineImpl
from memora.rag.engine import RAGEngineImpl
from memora.prompt.engine import PromptEngineImpl
from memora.models.memory import Memory, MemoryType


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


# ── Fixtures ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def search_service(tmp_path) -> tuple[SearchServiceImpl, MemoryEngineImpl]:
    from memora.storage import create_storage

    storage = await create_storage(
        str(tmp_path / "test.db"),
        str(tmp_path / "chroma"),
    )
    llm = StubLLM()
    memory = MemoryEngineImpl(storage, llm)
    rag = RAGEngineImpl(storage, llm)
    prompt = PromptEngineImpl(storage, llm)
    search = SearchServiceImpl(memory, rag, prompt)
    yield search, memory
    await storage.close()


# ── Tests ────────────────────────────────────────────────────

class TestSearchServiceProtocol:
    @pytest.mark.asyncio
    async def test_satisfies_protocol(self, search_service):
        search, _ = search_service
        assert isinstance(search, SearchService)


class TestUnifiedSearch:
    @pytest.mark.asyncio
    async def test_search_memory_only(self, search_service):
        search, memory = search_service
        await memory.save(Memory(content="Python is great", memory_type=MemoryType.FACT, source="test"))

        results = await search.search("Python", scope="memory")
        assert len(results) > 0
        assert all(r.source_type == "memory" for r in results)

    @pytest.mark.asyncio
    async def test_search_empty(self, search_service):
        search, _ = search_service
        results = await search.search("nothing here")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_respects_scope(self, search_service):
        search, memory = search_service
        await memory.save(Memory(content="test memory", memory_type=MemoryType.FACT, source="test"))

        # Scope "knowledge" should not return memories
        results = await search.search("test", scope="knowledge")
        memory_results = [r for r in results if r.source_type == "memory"]
        assert len(memory_results) == 0

    @pytest.mark.asyncio
    async def test_search_all_scopes(self, search_service):
        search, memory = search_service
        await memory.save(Memory(content="Python backend", memory_type=MemoryType.FACT, source="test"))

        results = await search.search("Python", scope="all")
        assert len(results) > 0
