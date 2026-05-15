"""Tests for Prompt engine."""

import pytest
import pytest_asyncio

from memora.prompt import PromptEngine
from memora.prompt.engine import PromptEngineImpl
from memora.models.prompt import Prompt, PromptVersion
from memora.storage import Storage


# ── Stub LLM ─────────────────────────────────────────────────

class StubLLM:
    async def chat(self, messages, temperature=0.7):
        return '{"suggestions": ["Be more specific"], "optimized": "Optimized prompt"}'

    async def extract_memories(self, messages):
        return []

    async def embed(self, text):
        return [0.0] * 8

    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]


# ── Fixtures ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def engine(tmp_path) -> tuple[PromptEngineImpl, StubLLM]:
    from memora.storage import create_storage

    storage = await create_storage(
        str(tmp_path / "test.db"),
        str(tmp_path / "chroma"),
    )
    llm = StubLLM()
    eng = PromptEngineImpl(storage, llm)
    yield eng, llm
    await storage.close()


# ── Tests ────────────────────────────────────────────────────

class TestPromptEngineProtocol:
    @pytest.mark.asyncio
    async def test_satisfies_protocol(self, engine):
        eng, _ = engine
        assert isinstance(eng, PromptEngine)


class TestSaveAndGet:
    @pytest.mark.asyncio
    async def test_save_new_prompt(self, engine):
        eng, _ = engine
        prompt = await eng.save(
            "code-review",
            "You are a code reviewer. Review: {{code}}",
            description="Code review assistant",
            variables=["code"],
            tags=["code", "review"],
        )
        assert prompt.name == "code-review"
        assert prompt.latest_version == 1
        assert prompt.tags == ["code", "review"]

    @pytest.mark.asyncio
    async def test_get_latest_version(self, engine):
        eng, _ = engine
        await eng.save("test", "v1 content")
        await eng.save("test", "v2 content")

        prompt, version = await eng.get("test")
        assert prompt.latest_version == 2
        assert version.version == 2
        assert version.content == "v2 content"

    @pytest.mark.asyncio
    async def test_get_specific_version(self, engine):
        eng, _ = engine
        await eng.save("test", "v1 content")
        await eng.save("test", "v2 content")

        _, version = await eng.get("test", version=1)
        assert version.version == 1
        assert version.content == "v1 content"

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises(self, engine):
        eng, _ = engine
        with pytest.raises(ValueError, match="not found"):
            await eng.get("nonexistent")


class TestVersioning:
    @pytest.mark.asyncio
    async def test_auto_increment_version(self, engine):
        eng, _ = engine
        p1 = await eng.save("test", "v1")
        p2 = await eng.save("test", "v2")
        p3 = await eng.save("test", "v3")

        assert p1.latest_version == 1
        assert p2.latest_version == 2
        assert p3.latest_version == 3

    @pytest.mark.asyncio
    async def test_all_versions_preserved(self, engine):
        eng, _ = engine
        await eng.save("test", "v1 content")
        await eng.save("test", "v2 content")
        await eng.save("test", "v3 content")

        # Get each version
        _, v1 = await eng.get("test", version=1)
        _, v2 = await eng.get("test", version=2)
        _, v3 = await eng.get("test", version=3)

        assert v1.content == "v1 content"
        assert v2.content == "v2 content"
        assert v3.content == "v3 content"

    @pytest.mark.asyncio
    async def test_variables_stored(self, engine):
        eng, _ = engine
        await eng.save("test", "Hello {{name}}, your role is {{role}}", variables=["name", "role"])

        _, version = await eng.get("test")
        assert version.variables == ["name", "role"]


class TestList:
    @pytest.mark.asyncio
    async def test_list_all(self, engine):
        eng, _ = engine
        await eng.save("prompt-a", "content a")
        await eng.save("prompt-b", "content b")
        await eng.save("prompt-c", "content c")

        prompts = await eng.list()
        assert len(prompts) == 3

    @pytest.mark.asyncio
    async def test_list_by_tag(self, engine):
        eng, _ = engine
        await eng.save("a", "content", tags=["code"])
        await eng.save("b", "content", tags=["writing"])
        await eng.save("c", "content", tags=["code", "review"])

        results = await eng.list(tag="code")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_empty(self, engine):
        eng, _ = engine
        assert await eng.list() == []


class TestScore:
    @pytest.mark.asyncio
    async def test_score_version(self, engine):
        eng, _ = engine
        await eng.save("test", "content")
        await eng.score("test", version=1, score=4.5)

        _, version = await eng.get("test", version=1)
        assert version.score == 4.5

    @pytest.mark.asyncio
    async def test_score_out_of_range_raises(self, engine):
        eng, _ = engine
        await eng.save("test", "content")

        with pytest.raises(ValueError, match="between 1 and 5"):
            await eng.score("test", version=1, score=0.5)

        with pytest.raises(ValueError, match="between 1 and 5"):
            await eng.score("test", version=1, score=6.0)


class TestCompare:
    @pytest.mark.asyncio
    async def test_compare_versions(self, engine):
        eng, _ = engine
        await eng.save("test", "original prompt")
        await eng.score("test", version=1, score=3.0)
        await eng.save("test", "improved prompt")
        await eng.score("test", version=2, score=4.5)

        diff = await eng.compare("test", v1=1, v2=2)
        assert diff["content_changed"] is True
        assert diff["score_diff"] == 1.5
        assert diff["v1"]["content"] == "original prompt"
        assert diff["v2"]["content"] == "improved prompt"


class TestOptimize:
    @pytest.mark.asyncio
    async def test_optimize_returns_suggestions(self, engine):
        eng, _ = engine
        await eng.save("test", "You are a helpful assistant.")

        result = await eng.optimize("test", feedback="Too generic")
        assert "Optimized" in result or "suggestions" in result.lower()


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_prompt(self, engine):
        eng, _ = engine
        await eng.save("test", "v1")
        await eng.save("test", "v2")

        result = await eng.delete("test")
        assert result is True

        prompts = await eng.list()
        assert len(prompts) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, engine):
        eng, _ = engine
        result = await eng.delete("nonexistent")
        assert result is False
