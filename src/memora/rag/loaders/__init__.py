"""Document loaders — registry and base interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class LoaderResult:
    """Result from a document loader."""
    def __init__(self, content: str, metadata: dict) -> None:
        self.content = content
        self.metadata = metadata


class BaseLoader(ABC):
    """Abstract base for document loaders."""

    @abstractmethod
    def can_load(self, path_or_url: str) -> bool:
        """Return True if this loader handles the given path/URL."""
        ...

    @abstractmethod
    async def load(self, path_or_url: str) -> LoaderResult:
        """Load document content and metadata."""
        ...


class LoaderRegistry:
    """Registry of document loaders. Selects the right loader for a path/URL."""

    def __init__(self) -> None:
        self._loaders: list[BaseLoader] = []

    def register(self, loader: BaseLoader) -> None:
        """Add a loader to the registry."""
        self._loaders.append(loader)

    def get_loader(self, path_or_url: str) -> BaseLoader:
        """Find a loader that can handle the given path/URL."""
        for loader in self._loaders:
            if loader.can_load(path_or_url):
                return loader
        raise ValueError(f"No loader found for: {path_or_url}")


def create_default_registry() -> LoaderRegistry:
    """Create a LoaderRegistry with all built-in loaders."""
    from .markdown import MarkdownLoader
    from .text import TextLoader

    registry = LoaderRegistry()
    registry.register(MarkdownLoader())
    registry.register(TextLoader())  # fallback
    return registry
