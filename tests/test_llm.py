"""Tests for LLM client and prompt template loading."""

import json
import pytest

from memora.llm import (
    ExtractedMemory,
    ExtractedMemoryItem,
    PromptTemplate,
    DashScopeLLM,
    create_llm_client,
    LLMClient,
)


class TestPromptTemplate:
    def test_load_existing_template(self):
        tpl = PromptTemplate()
        data = tpl.load("memory_extract")
        assert "system" in data
        assert "user" in data

    def test_load_nonexistent_raises(self):
        tpl = PromptTemplate()
        with pytest.raises(FileNotFoundError):
            tpl.load("nonexistent_template")

    def test_render_substitutes_variables(self):
        tpl = PromptTemplate()
        system, user = tpl.render("memory_extract", messages="hello world")
        assert "hello world" in user
        assert "{messages}" not in user

    def test_render_caches_template(self):
        tpl = PromptTemplate()
        tpl.load("memory_extract")
        assert "memory_extract" in tpl._cache

    def test_render_all_templates(self):
        """Verify all 4 prompt templates load without error."""
        tpl = PromptTemplate()
        for name in ("memory_extract", "memory_summarize", "rag_query", "prompt_optimize"):
            data = tpl.load(name)
            assert "system" in data or "user" in data


class TestExtractedMemoryItem:
    def test_create(self):
        item = ExtractedMemoryItem(content="test", memory_type="fact", confidence=0.9)
        assert item.content == "test"
        assert item.memory_type == "fact"
        assert item.confidence == 0.9

    def test_default_confidence(self):
        item = ExtractedMemoryItem(content="test", memory_type="fact")
        assert item.confidence == 1.0

    def test_confidence_validation(self):
        with pytest.raises(Exception):
            ExtractedMemoryItem(content="test", memory_type="fact", confidence=2.0)


class TestExtractedMemory:
    def test_create(self):
        m = ExtractedMemory(content="test", memory_type="fact", confidence=0.8)
        assert m.content == "test"
        assert m.memory_type == "fact"
        assert m.confidence == 0.8


class TestDashScopeLLMParseMemories:
    """Test the _parse_memories method without hitting the LLM API."""

    def _make_client(self) -> DashScopeLLM:
        return DashScopeLLM(
            base_url="http://test",
            api_key="test-key",
            model="test",
            embedding_model="test",
        )

    def test_parse_valid_json_array(self):
        client = self._make_client()
        raw = json.dumps([
            {"content": "user likes Python", "memory_type": "preference", "confidence": 0.9},
            {"content": "project uses Vue 3", "memory_type": "decision", "confidence": 1.0},
        ])
        result = client._parse_memories(raw)
        assert len(result) == 2
        assert result[0].content == "user likes Python"
        assert result[1].memory_type == "decision"

    def test_parse_json_object_with_memories_key(self):
        client = self._make_client()
        raw = json.dumps({
            "memories": [
                {"content": "deployed on AWS", "memory_type": "fact"},
            ]
        })
        result = client._parse_memories(raw)
        assert len(result) == 1
        assert result[0].content == "deployed on AWS"

    def test_parse_markdown_code_block(self):
        client = self._make_client()
        raw = '```json\n[{"content": "test", "memory_type": "fact"}]\n```'
        result = client._parse_memories(raw)
        assert len(result) == 1

    def test_parse_invalid_json_returns_empty(self):
        client = self._make_client()
        result = client._parse_memories("not valid json at all")
        assert result == []

    def test_parse_skips_invalid_memory_type(self):
        client = self._make_client()
        raw = json.dumps([
            {"content": "valid", "memory_type": "fact"},
            {"content": "invalid", "memory_type": "unknown_type"},
        ])
        result = client._parse_memories(raw)
        assert len(result) == 1
        assert result[0].content == "valid"

    def test_parse_skips_items_without_content(self):
        client = self._make_client()
        raw = json.dumps([
            {"memory_type": "fact"},  # missing content
            {"content": "valid", "memory_type": "fact"},
        ])
        result = client._parse_memories(raw)
        assert len(result) == 1


class TestCreateLLMClient:
    def test_returns_dashscope_instance(self):
        llm = create_llm_client(
            base_url="http://test",
            api_key="test-key",
            model="test-model",
            embedding_model="test-embed",
        )
        assert isinstance(llm, DashScopeLLM)
        assert isinstance(llm, LLMClient)

    def test_uses_provided_config(self):
        llm = create_llm_client(
            base_url="http://custom-url",
            api_key="custom-key",
            model="custom-model",
            embedding_model="custom-embed",
        )
        assert llm._chat.model_name == "custom-model"
