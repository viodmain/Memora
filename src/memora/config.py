"""Application configuration loader."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class LLMConfig:
    provider: str = "dashscope"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: str = ""
    model: str = "qwen-plus"
    embedding_model: str = "text-embedding-v3"


@dataclass
class StorageConfig:
    db_path: str = "data/memora.db"
    chroma_path: str = "data/chroma"


@dataclass
class MemoryExtractionConfig:
    auto_extract: bool = True
    min_messages: int = 3
    extract_types: list[str] = field(default_factory=lambda: ["fact", "preference", "decision", "experience"])
    dedup_threshold: float = 0.9
    merge_similar: bool = True


@dataclass
class RAGConfig:
    chunk_size: int = 512
    chunk_overlap: int = 64


@dataclass
class MCPConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class AppConfig:
    name: str = "Memora"
    version: str = "0.1.0"
    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    memory_extraction: MemoryExtractionConfig = field(default_factory=MemoryExtractionConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)


def _resolve_env_vars(value: str) -> str:
    """Resolve ${ENV_VAR} placeholders in string values."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_key = value[2:-1]
        return os.environ.get(env_key, "")
    return value


def _apply_env_vars(data: dict) -> dict:
    """Recursively resolve environment variable placeholders."""
    resolved = {}
    for key, value in data.items():
        if isinstance(value, dict):
            resolved[key] = _apply_env_vars(value)
        elif isinstance(value, str):
            resolved[key] = _resolve_env_vars(value)
        else:
            resolved[key] = value
    return resolved


def _build_config(data: dict) -> AppConfig:
    """Build AppConfig from a flat dictionary."""
    data = _apply_env_vars(data)

    llm_data = data.get("llm", {})
    storage_data = data.get("storage", {})
    mem_data = data.get("memory_extraction", {})
    rag_data = data.get("rag", {})
    mcp_data = data.get("mcp", {})
    app_data = data.get("app", {})

    return AppConfig(
        name=app_data.get("name", "Memora"),
        version=app_data.get("version", "0.1.0"),
        llm=LLMConfig(**{k: v for k, v in llm_data.items() if k in LLMConfig.__dataclass_fields__}),
        storage=StorageConfig(**{k: v for k, v in storage_data.items() if k in StorageConfig.__dataclass_fields__}),
        memory_extraction=MemoryExtractionConfig(
            **{k: v for k, v in mem_data.items() if k in MemoryExtractionConfig.__dataclass_fields__}
        ),
        rag=RAGConfig(**{k: v for k, v in rag_data.items() if k in RAGConfig.__dataclass_fields__}),
        mcp=MCPConfig(**{k: v for k, v in mcp_data.items() if k in MCPConfig.__dataclass_fields__}),
    )


def load_config(config_path: str = "config/settings.yaml") -> AppConfig:
    """Load application configuration from YAML file.

    Args:
        config_path: Path to the settings YAML file.

    Returns:
        AppConfig instance with resolved values.
    """
    load_dotenv()

    path = Path(config_path)
    if not path.exists():
        return AppConfig()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _build_config(data)
