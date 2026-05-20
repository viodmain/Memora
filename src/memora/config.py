"""Application configuration loader."""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv


# ── Platform-specific data directory ─────────────────────────

def get_data_dir() -> Path:
    """Get platform-specific data directory for Memora.

    Windows:  %APPDATA%/memora/
    macOS:    ~/Library/Application Support/memora/
    Linux:    ~/.local/share/memora/

    Override with MEMORA_DATA_DIR environment variable.
    """
    # Environment variable override takes priority
    env_dir = os.environ.get("MEMORA_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"

    return base / "memora"


# ── Data models ──────────────────────────────────────────────

@dataclass
class LLMConfig:
    provider: str = "dashscope"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: str = ""
    model: str = "qwen-plus"
    embedding_model: str = "text-embedding-v3"


@dataclass
class EmbeddingConfig:
    """Separate embedding provider config. Falls back to LLM provider if not set."""
    provider: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = "text-embedding-v3"


@dataclass
class StorageConfig:
    db_path: str = ""
    chroma_path: str = ""

    def __post_init__(self):
        data_dir = get_data_dir()
        if not self.db_path:
            self.db_path = str(data_dir / "memora.db")
        if not self.chroma_path:
            self.chroma_path = str(data_dir / "chroma")


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
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    memory_extraction: MemoryExtractionConfig = field(default_factory=MemoryExtractionConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)


# ── Helpers ──────────────────────────────────────────────────

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
    embed_data = data.get("embedding", {})
    storage_data = data.get("storage", {})
    mem_data = data.get("memory_extraction", {})
    rag_data = data.get("rag", {})
    mcp_data = data.get("mcp", {})
    app_data = data.get("app", {})

    return AppConfig(
        name=app_data.get("name", "Memora"),
        version=app_data.get("version", "0.1.0"),
        llm=LLMConfig(**{k: v for k, v in llm_data.items() if k in LLMConfig.__dataclass_fields__}),
        embedding=EmbeddingConfig(**{k: v for k, v in embed_data.items() if k in EmbeddingConfig.__dataclass_fields__}),
        storage=StorageConfig(**{k: v for k, v in storage_data.items() if k in StorageConfig.__dataclass_fields__}),
        memory_extraction=MemoryExtractionConfig(
            **{k: v for k, v in mem_data.items() if k in MemoryExtractionConfig.__dataclass_fields__}
        ),
        rag=RAGConfig(**{k: v for k, v in rag_data.items() if k in RAGConfig.__dataclass_fields__}),
        mcp=MCPConfig(**{k: v for k, v in mcp_data.items() if k in MCPConfig.__dataclass_fields__}),
    )


def _load_env():
    """Load .env file. Priority: env vars already set > data dir > cwd > package dir."""
    data_dir = get_data_dir()

    env_locations = [
        data_dir / ".env",                  # Data directory (recommended)
        Path(".env"),                       # Current working directory
    ]
    for env_path in env_locations:
        if env_path.exists():
            load_dotenv(env_path, override=False)  # Don't override existing env vars
            break


def load_config(config_path: str = "") -> AppConfig:
    """Load application configuration.

    Priority order:
    1. Environment variables (always take priority)
    2. config/settings.yaml (if exists)
    3. Default values

    .env loading priority:
    1. MEMORA_DATA_DIR/.env
    2. Current working directory/.env

    Args:
        config_path: Path to settings YAML. If empty, uses default locations.

    Returns:
        AppConfig instance with resolved values.
    """
    _load_env()

    # Search for settings.yaml
    if not config_path:
        candidates = [
            get_data_dir() / "settings.yaml",
            Path("config/settings.yaml"),
        ]
        for c in candidates:
            if c.exists():
                config_path = str(c)
                break

    if not config_path or not Path(config_path).exists():
        return AppConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _build_config(data)
