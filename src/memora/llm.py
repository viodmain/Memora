"""LLM client abstraction and DashScope (OpenAI-compatible) implementation.

The LLMClient Protocol defines the interface that all engine modules use.
DashScopeLLM implements it via langchain-openai's ChatOpenAI, which works
with any OpenAI-compatible API endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import yaml
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


# ── Data structures ──────────────────────────────────────────

@dataclass
class ExtractedMemory:
    """A single memory extracted from conversation by the LLM."""
    content: str
    memory_type: str
    confidence: float


class MemoryExtractionResult(BaseModel):
    """Structured output schema for memory extraction."""
    memories: list[ExtractedMemoryItem] = Field(default_factory=list)


class ExtractedMemoryItem(BaseModel):
    """Single memory item in the extraction result."""
    content: str
    memory_type: str = Field(description="One of: fact, preference, decision, experience, relationship")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ── Protocol ─────────────────────────────────────────────────

@runtime_checkable
class LLMClient(Protocol):
    """Interface for LLM operations used by engine modules.

    Implementations hide the specific provider (DashScope, OpenAI, etc.)
    behind this uniform API.
    """

    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Plain chat completion. messages: [{"role": ..., "content": ...}]"""
        ...

    async def extract_memories(self, messages: list[dict]) -> list[ExtractedMemory]:
        """Extract memories from conversation via structured output."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        ...


# ── Prompt template loader ───────────────────────────────────

class PromptTemplate:
    """Load and render YAML prompt templates from config/prompts/."""

    def __init__(self, templates_dir: str = "config/prompts") -> None:
        self._dir = Path(templates_dir)
        self._cache: dict[str, dict] = {}

    def load(self, name: str) -> dict:
        """Load a prompt template by name. Returns {"system": ..., "user": ...}."""
        if name not in self._cache:
            path = self._dir / f"{name}.yaml"
            if not path.exists():
                raise FileNotFoundError(f"Prompt template not found: {path}")
            with open(path, "r", encoding="utf-8") as f:
                self._cache[name] = yaml.safe_load(f)
        return self._cache[name]

    def render(self, name: str, **kwargs) -> tuple[str, str]:
        """Load and render a template with variables. Returns (system, user)."""
        tpl = self.load(name)
        system = tpl.get("system", "").strip()
        user = tpl.get("user", "").strip()
        # Substitute {variable} placeholders
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            system = system.replace(placeholder, str(value))
            user = user.replace(placeholder, str(value))
        return system, user


# ── DashScope / OpenAI-compatible implementation ─────────────

class DashScopeLLM:
    """LLMClient implementation using langchain-openai (OpenAI-compatible).

    Works with DashScope, OpenAI, DeepSeek, Ollama, or any provider
    that exposes an OpenAI-compatible chat/embeddings endpoint.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "qwen-plus",
        embedding_model: str = "text-embedding-v3",
        templates_dir: str = "config/prompts",
    ) -> None:
        self._chat = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=0.7,
        )
        self._embeddings = OpenAIEmbeddings(
            base_url=base_url,
            api_key=api_key,
            model=embedding_model,
        )
        self._templates = PromptTemplate(templates_dir)

    async def chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Send messages to the LLM and return the response text."""
        self._chat.temperature = temperature
        lc_messages = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            else:
                lc_messages.append(HumanMessage(content=m["content"]))
        resp = await self._chat.ainvoke(lc_messages)
        return resp.content

    async def extract_memories(self, messages: list[dict]) -> list[ExtractedMemory]:
        """Extract memories from conversation using the memory_extract prompt.

        Formats the conversation, sends it to the LLM with the extraction
        prompt template, and parses the JSON response into ExtractedMemory objects.
        """
        conversation = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        system, user = self._templates.render("memory_extract", messages=conversation)

        raw = await self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], temperature=0.3)

        return self._parse_memories(raw)

    def _parse_memories(self, raw: str) -> list[ExtractedMemory]:
        """Parse LLM JSON response into ExtractedMemory list."""
        import json
        # Try to extract JSON from the response (handle markdown code blocks)
        text = raw.strip()
        if text.startswith("```"):
            # Remove markdown code block wrapper
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        items = data if isinstance(data, list) else data.get("memories", [])
        results = []
        for item in items:
            if isinstance(item, dict) and "content" in item and "memory_type" in item:
                mt = item["memory_type"]
                if mt in ("fact", "preference", "decision", "experience", "relationship"):
                    results.append(ExtractedMemory(
                        content=item["content"],
                        memory_type=mt,
                        confidence=float(item.get("confidence", 1.0)),
                    ))
        return results

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        return await self._embeddings.aembed_query(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings."""
        return await self._embeddings.aembed_documents(texts)


# ── Factory ──────────────────────────────────────────────────

def create_llm_client(
    base_url: str,
    api_key: str,
    model: str = "qwen-plus",
    embedding_model: str = "text-embedding-v3",
    templates_dir: str = "config/prompts",
) -> DashScopeLLM:
    """Factory: create an LLMClient instance from config values."""
    return DashScopeLLM(
        base_url=base_url,
        api_key=api_key,
        model=model,
        embedding_model=embedding_model,
        templates_dir=templates_dir,
    )
