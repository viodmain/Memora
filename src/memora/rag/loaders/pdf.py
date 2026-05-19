"""PDF file loader."""

from __future__ import annotations

from pathlib import Path

from . import BaseLoader, LoaderResult


class PDFLoader(BaseLoader):
    """Load PDF files using pypdf2."""

    def can_load(self, path_or_url: str) -> bool:
        return Path(path_or_url).suffix.lower() == ".pdf"

    async def load(self, path_or_url: str) -> LoaderResult:
        from pypdf2 import PdfReader

        path = Path(path_or_url)
        reader = PdfReader(str(path))

        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(f"[Page {i + 1}]\n{text}")

        content = "\n\n".join(pages)
        return LoaderResult(
            content=content,
            metadata={
                "title": path.stem,
                "source_path": str(path),
                "source_type": "file",
                "file_type": "pdf",
                "page_count": len(reader.pages),
            },
        )
