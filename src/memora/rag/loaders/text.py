"""Plain text file loader (fallback)."""

from __future__ import annotations

from pathlib import Path

from . import BaseLoader, LoaderResult


class TextLoader(BaseLoader):
    """Load plain text files (.txt, .py, .js, .json, .yaml, etc.)."""

    SUPPORTED_SUFFIXES = {".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh", ".bash"}

    def can_load(self, path_or_url: str) -> bool:
        return Path(path_or_url).suffix.lower() in self.SUPPORTED_SUFFIXES

    async def load(self, path_or_url: str) -> LoaderResult:
        path = Path(path_or_url)
        content = path.read_text(encoding="utf-8")
        return LoaderResult(
            content=content,
            metadata={
                "title": path.stem,
                "source_path": str(path),
                "source_type": "file",
                "file_type": path.suffix.lstrip("."),
            },
        )
