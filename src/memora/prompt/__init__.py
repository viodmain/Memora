"""Prompt engine — Protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from memora.models.prompt import Prompt, PromptVersion


@runtime_checkable
class PromptEngine(Protocol):
    """Interface for prompt template management with versioning."""

    async def save(
        self,
        name: str,
        content: str,
        description: str = "",
        variables: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Prompt:
        """Save a prompt. Creates new version if name exists."""
        ...

    async def get(self, name: str, version: int | None = None) -> tuple[Prompt, PromptVersion]:
        """Get prompt metadata + specified version (default: latest)."""
        ...

    async def list(self, tag: str | None = None) -> list[Prompt]:
        """List prompts, optionally filtered by tag."""
        ...

    async def score(self, name: str, version: int, score: float) -> None:
        """Rate a prompt version (1-5)."""
        ...

    async def compare(self, name: str, v1: int, v2: int) -> dict:
        """Compare two versions. Returns diff info."""
        ...

    async def optimize(self, name: str, feedback: str = "") -> str:
        """Generate optimization suggestions via LLM."""
        ...

    async def delete(self, name: str) -> bool:
        """Delete a prompt and all its versions."""
        ...
