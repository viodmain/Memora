"""Tests for Pydantic data models."""

import pytest
from datetime import datetime

from memora.models.memory import Memory, MemoryType, ConversationSummary
from memora.models.document import Document, DocumentChunk
from memora.models.prompt import Prompt, PromptVersion
from memora.models.search import SearchResult


class TestMemory:
    def test_create_with_defaults(self):
        m = Memory(content="test", memory_type=MemoryType.FACT)
        assert m.id  # auto-generated
        assert m.content == "test"
        assert m.memory_type == MemoryType.FACT
        assert m.confidence == 1.0
        assert m.tags == []
        assert m.access_count == 0
        assert isinstance(m.created_at, datetime)

    def test_all_memory_types(self):
        for mt in MemoryType:
            m = Memory(content=f"type {mt}", memory_type=mt)
            assert m.memory_type == mt

    def test_confidence_validation(self):
        m = Memory(content="c", memory_type=MemoryType.FACT, confidence=0.5)
        assert m.confidence == 0.5

        with pytest.raises(Exception):
            Memory(content="c", memory_type=MemoryType.FACT, confidence=1.5)

        with pytest.raises(Exception):
            Memory(content="c", memory_type=MemoryType.FACT, confidence=-0.1)

    def test_serialization_roundtrip(self):
        m = Memory(content="roundtrip", memory_type=MemoryType.DECISION, tags=["a", "b"])
        data = m.model_dump()
        m2 = Memory(**data)
        assert m2.content == m.content
        assert m2.tags == m.tags
        assert m2.id == m.id

    def test_conversation_summary(self):
        cs = ConversationSummary(title="Test", summary="A summary", key_points=["a", "b"])
        assert cs.id
        assert cs.key_points == ["a", "b"]
        assert cs.memory_ids == []


class TestDocument:
    def test_create_document(self):
        d = Document(title="README", source_path="/tmp/readme.md", source_type="file", file_type="md")
        assert d.id
        assert d.chunk_count == 0
        assert d.metadata == {}

    def test_document_chunk(self):
        c = DocumentChunk(document_id="doc1", content="chunk text", chunk_index=0)
        assert c.id
        assert c.document_id == "doc1"


class TestPrompt:
    def test_create_prompt(self):
        p = Prompt(name="test-prompt")
        assert p.id
        assert p.name == "test-prompt"
        assert p.latest_version == 0

    def test_prompt_version(self):
        pv = PromptVersion(prompt_id="p1", version=1, content="Hello {{name}}")
        assert pv.id
        assert pv.variables == []
        assert pv.score is None


class TestSearchResult:
    def test_create_search_result(self):
        sr = SearchResult(
            content="found text",
            source_type="memory",
            source_id="mem1",
            relevance_score=0.95,
        )
        assert sr.source_type == "memory"
        assert sr.metadata == {}
