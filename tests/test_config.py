"""Tests for configuration loading."""

import os
import tempfile
import yaml
import pytest

from memora.config import load_config, AppConfig, _resolve_env_vars, _build_config


class TestResolveEnvVars:
    def test_resolves_existing_env(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "hello")
        assert _resolve_env_vars("${TEST_KEY}") == "hello"

    def test_returns_empty_for_missing_env(self, monkeypatch):
        monkeypatch.delenv("MISSING_KEY", raising=False)
        assert _resolve_env_vars("${MISSING_KEY}") == ""

    def test_leaves_normal_string_unchanged(self):
        assert _resolve_env_vars("plain text") == "plain text"


class TestBuildConfig:
    def test_defaults_when_empty(self):
        cfg = _build_config({})
        assert cfg.name == "Memora"
        assert cfg.llm.provider == "dashscope"
        assert cfg.storage.db_path.endswith("memora.db")
        assert "memora" in cfg.storage.chroma_path

    def test_partial_override(self):
        cfg = _build_config({"llm": {"model": "qwen-turbo"}})
        assert cfg.llm.model == "qwen-turbo"
        assert cfg.llm.provider == "dashscope"  # default preserved

    def test_full_override(self):
        data = {
            "app": {"name": "TestApp", "version": "2.0"},
            "llm": {"provider": "openai", "model": "gpt-4"},
            "storage": {"db_path": "/tmp/test.db"},
            "memory_extraction": {"dedup_threshold": 0.8},
            "rag": {"chunk_size": 256},
            "mcp": {"port": 9999},
        }
        cfg = _build_config(data)
        assert cfg.name == "TestApp"
        assert cfg.version == "2.0"
        assert cfg.llm.provider == "openai"
        assert cfg.llm.model == "gpt-4"
        assert cfg.storage.db_path == "/tmp/test.db"
        assert cfg.memory_extraction.dedup_threshold == 0.8
        assert cfg.rag.chunk_size == 256
        assert cfg.mcp.port == 9999


class TestLoadConfig:
    def test_returns_defaults_when_file_missing(self):
        cfg = load_config("/nonexistent/path.yaml")
        assert cfg.name == "Memora"

    def test_loads_from_yaml_file(self, tmp_path):
        config_data = {"app": {"name": "FromFile"}, "llm": {"model": "custom"}}
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_config(str(config_file))
        assert cfg.name == "FromFile"
        assert cfg.llm.model == "custom"

    def test_resolves_env_vars_in_yaml(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_API_KEY", "sk-test-123")
        config_data = {"llm": {"api_key": "${MY_API_KEY}"}}
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(yaml.dump(config_data))

        cfg = load_config(str(config_file))
        assert cfg.llm.api_key == "sk-test-123"
