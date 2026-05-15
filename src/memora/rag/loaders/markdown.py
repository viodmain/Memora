"""Markdown file loader."""

from __future__ import annotations

from pathlib import Path

from . import BaseLoader, LoaderResult


class MarkdownLoader(BaseLoader):
    """Load .md files."""

    def can_load(self, path_or_url: str) -> bool:
        return Path(path_or_url).suffix.lower() in (".md", ".markdown", ".mdx")

    async def load(self, path_or_url: str) -> LoaderResult:
        path = Path(path_or_url)
        content = path.read_text(encoding="utf-8")
        return LoaderResult(
            content=content,
            metadata={
                "title": path.stem,
                "source_path": str(path),
                "source_type": "file",
                "file_type": "md",
            },
        )
