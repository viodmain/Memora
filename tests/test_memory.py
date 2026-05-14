"""Tests for Memory engine."""

import pytest
import pytest_asyncio

from memora.memory import MemoryEngine
from memora.memory.engine import MemoryEngineImpl
from memora.models.memory import Memory, MemoryType, ConversationSummary
from memora.storage import Storage
from memora.llm import ExtractedMemory


# ── Stub LLM client for testing ──────────────────────────────

class StubLLM:
    """Minimal LLM stub that returns predictable results."""

    def __init__(self):
        self.embed_calls: list[str] = []
        self.extract_calls: list[list[dict]] = []
        self.chat_calls: list[list[dict]] = []
        self._extract_result: list[ExtractedMemory] = []
        self._embed_dim = 8

    def set_extract_result(self, items: list[ExtractedMemory]):
        self._extract_result = items

    async def chat(self, messages, temperature=0.7):
        self.chat_calls.append(messages)
        return '{"title": "Test", "summary": "A summary", "key_points": ["point1"]}'

    async def extract_memories(self, messages):
        self.extract_calls.append(messages)
        return list(self._extract_result)

    async def embed(self, text):
        self.embed_calls.append(text)
        # Deterministic pseudo-embedding based on text content
        vec = [0.0] * self._embed_dim
        for i, ch in enumerate(text[:self._embed_dim]):
            vec[i] = (ord(ch) % 100) / 100.0
        return vec

    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]


# ── Fixtures ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def engine(tmp_path) -> tuple[MemoryEngineImpl, StubLLM]:
    """Create a MemoryEngineImpl with stub LLM and temp storage."""
    from memora.storage import create_storage

    storage = await create_storage(
        str(tmp_path / "test.db"),
        str(tmp_path / "chroma"),
    )
    llm = StubLLM()
    eng = MemoryEngineImpl(storage, llm, dedup_threshold=0.9)
    yield eng, llm
    await storage.close()


def _make_memory(content: str = "test memory", mt: MemoryType = MemoryType.FACT) -> Memory:
    return Memory(content=content, memory_type=mt, source="test")


# ── Tests ────────────────────────────────────────────────────

class TestMemoryEngineProtocol:
    @pytest.mark.asyncio
    async def test_satisfies_protocol(self, engine):
        eng, _ = engine
        assert isinstance(eng, MemoryEngine)


class TestSaveAndGet:
    @pytest.mark.asyncio
    async def test_save_and_get(self, engine):
        eng, llm = engine
        m = _make_memory("user prefers Python", MemoryType.PREFERENCE)
        saved = await eng.save(m)
        assert saved.id == m.id

        fetched = await eng.get(m.id)
        assert fetched is not None
        assert fetched.content == "user prefers Python"
        assert fetched.memory_type == MemoryType.PREFERENCE
        assert len(llm.embed_calls) == 1  # embed was called

    @pytest.mark.asyncio
    async def test_get_increments_access_count(self, engine):
        eng, _ = engine
        m = _make_memory("visit count test")
        await eng.save(m)

        await eng.get(m.id)
        await eng.get(m.id)
        fetched = await eng.get(m.id)
        assert fetched.access_count == 3

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, engine):
        eng, _ = engine
        assert await eng.get("nonexistent") is None


class TestList:
    @pytest.mark.asyncio
    async def test_list_all(self, engine):
        eng, _ = engine
        for i in range(3):
            await eng.save(_make_memory(f"memory {i}"))
        result = await eng.list()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_by_type(self, engine):
        eng, _ = engine
        await eng.save(_make_memory("fact", MemoryType.FACT))
        await eng.save(_make_memory("pref", MemoryType.PREFERENCE))
        await eng.save(_make_memory("decision", MemoryType.DECISION))

        facts = await eng.list(memory_type=MemoryType.FACT)
        assert len(facts) == 1
        assert facts[0].memory_type == MemoryType.FACT

    @pytest.mark.asyncio
    async def test_list_limit_offset(self, engine):
        eng, _ = engine
        for i in range(5):
            await eng.save(_make_memory(f"memory {i}"))

        page1 = await eng.list(limit=2, offset=0)
        page2 = await eng.list(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_content(self, engine):
        eng, _ = engine
        m = _make_memory("original content")
        await eng.save(m)

        m.content = "updated content"
        m.memory_type = MemoryType.DECISION
        await eng.update(m)

        fetched = await eng.get(m.id)
        assert fetched.content == "updated content"
        assert fetched.memory_type == MemoryType.DECISION

    @pytest.mark.asyncio
    async def test_update_revectorizes(self, engine):
        eng, llm = engine
        m = _make_memory("original")
        await eng.save(m)
        embed_count_before = len(llm.embed_calls)

        m.content = "changed content"
        await eng.update(m)
        assert len(llm.embed_calls) == embed_count_before + 1


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_existing(self, engine):
        eng, _ = engine
        m = _make_memory("to delete")
        await eng.save(m)

        result = await eng.delete(m.id)
        assert result is True
        assert await eng.get(m.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, engine):
        eng, _ = engine
        result = await eng.delete("nonexistent")
        assert result is False


class TestExtractFromMessages:
    @pytest.mark.asyncio
    async def test_extract_saves_new_memories(self, engine):
        eng, llm = engine
        llm.set_extract_result([
            ExtractedMemory(content="user likes Go", memory_type="preference", confidence=0.9),
            ExtractedMemory(content="project uses Vue 3", memory_type="decision", confidence=1.0),
        ])

        messages = [
            {"role": "user", "content": "I prefer Go for backend"},
            {"role": "assistant", "content": "Got it, I'll use Go"},
        ]
        result = await eng.extract_from_messages(messages, source="test")

        assert len(result) == 2
        assert result[0].content == "user likes Go"
        assert result[0].source == "test"
        # Verify persisted
        all_memories = await eng.list()
        assert len(all_memories) == 2

    @pytest.mark.asyncio
    async def test_extract_deduplicates(self, engine):
        eng, llm = engine

        # First extraction
        llm.set_extract_result([
            ExtractedMemory(content="user likes Python", memory_type="preference", confidence=0.9),
        ])
        messages = [{"role": "user", "content": "I like Python"}]
        result1 = await eng.extract_from_messages(messages)
        assert len(result1) == 1

        # Second extraction with same content — should be deduplicated
        llm.set_extract_result([
            ExtractedMemory(content="user likes Python", memory_type="preference", confidence=0.9),
        ])
        result2 = await eng.extract_from_messages(messages)
        assert len(result2) == 0  # Deduped

    @pytest.mark.asyncio
    async def test_extract_empty_result(self, engine):
        eng, llm = engine
        llm.set_extract_result([])

        result = await eng.extract_from_messages([{"role": "user", "content": "hi"}])
        assert result == []


class TestRecall:
    @pytest.mark.asyncio
    async def test_recall_returns_similar_memories(self, engine):
        eng, _ = engine
        await eng.save(_make_memory("user prefers Python"))
        await eng.save(_make_memory("project uses Docker"))
        await eng.save(_make_memory("deployed on AWS"))

        results = await eng.recall("Python programming", top_k=2)
        assert len(results) <= 2
        assert all(isinstance(m, Memory) for m in results)

    @pytest.mark.asyncio
    async def test_recall_with_type_filter(self, engine):
        eng, _ = engine
        await eng.save(_make_memory("fact one", MemoryType.FACT))
        await eng.save(_make_memory("preference one", MemoryType.PREFERENCE))

        results = await eng.recall("one", top_k=5, memory_type=MemoryType.FACT)
        assert len(results) == 1
        assert results[0].memory_type == MemoryType.FACT

    @pytest.mark.asyncio
    async def test_recall_empty_when_no_memories(self, engine):
        eng, _ = engine
        results = await eng.recall("anything")
        assert results == []


class TestSummarizeConversation:
    @pytest.mark.asyncio
    async def test_summarize_returns_summary(self, engine):
        eng, llm = engine
        messages = [
            {"role": "user", "content": "Let's discuss the project architecture"},
            {"role": "assistant", "content": "Sure, I suggest using FastAPI"},
        ]
        summary = await eng.summarize_conversation(messages)

        assert isinstance(summary, ConversationSummary)
        assert summary.title == "Test"
        assert summary.summary == "A summary"
        assert len(llm.chat_calls) == 1
