"""Memory engine — Protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from memora.models.memory import Memory, MemoryType, ConversationSummary


@runtime_checkable
class MemoryEngine(Protocol):
    """Interface for memory operations: extraction, storage, retrieval."""

    async def save(self, memory: Memory) -> Memory:
        """Persist a single memory (SQLite + vectorize → ChromaDB)."""
        ...

    async def get(self, memory_id: str) -> Memory | None:
        """Retrieve a single memory by ID."""
        ...

    async def list(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Memory]:
        """List memories ordered by created_at DESC."""
        ...

    async def update(self, memory: Memory) -> Memory:
        """Update an existing memory's content and metadata."""
        ...

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if found."""
        ...

    async def extract_from_messages(
        self,
        messages: list[dict],
        source: str = "claude_code",
    ) -> list[Memory]:
        """Batch-extract memories from conversation messages.

        1. LLM extracts raw memories
        2. Dedup against existing memories (similarity > threshold → skip)
        3. Persist new memories
        """
        ...

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        memory_type: MemoryType | None = None,
    ) -> list[Memory]:
        """Semantic search: embed query → ChromaDB vector search → return memories."""
        ...

    async def summarize_conversation(
        self,
        messages: list[dict],
    ) -> ConversationSummary:
        """Generate a conversation summary via LLM."""
        ...
