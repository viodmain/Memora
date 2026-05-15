"""Text chunking strategies for document ingestion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    """A text chunk with optional metadata."""
    content: str
    metadata: dict


class TextChunker:
    """Split text into overlapping chunks.

    Uses a sliding window approach with configurable size and overlap.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: The full text to split.
            metadata: Base metadata to attach to each chunk.

        Returns:
            List of Chunk objects.
        """
        metadata = metadata or {}
        if not text.strip():
            return []

        # Split by paragraphs first, then merge into sized chunks
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks: list[Chunk] = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 1 <= self._chunk_size:
                current = f"{current}\n\n{para}" if current else para
            else:
                if current:
                    chunks.append(Chunk(content=current.strip(), metadata=dict(metadata)))
                # If a single paragraph exceeds chunk_size, split it further
                if len(para) > self._chunk_size:
                    sub_chunks = self._split_long_text(para)
                    for sc in sub_chunks:
                        chunks.append(Chunk(content=sc, metadata=dict(metadata)))
                    current = ""
                else:
                    current = para

        if current.strip():
            chunks.append(Chunk(content=current.strip(), metadata=dict(metadata)))

        return chunks

    def _split_long_text(self, text: str) -> list[str]:
        """Split a long text by sentences, with character-level fallback."""
        # Try sentence-level splitting first
        sentences = text.replace(". ", ".\n").replace(".\n", ".\n").split("\n")
        # If no real sentence breaks found, split by words
        if len(sentences) <= 1:
            words = text.split()
            sentences = []
            current = ""
            for word in words:
                if len(current) + len(word) + 1 <= self._chunk_size:
                    current = f"{current} {word}" if current else word
                else:
                    if current:
                        sentences.append(current)
                    current = word
            if current:
                sentences.append(current)

        chunks: list[str] = []
        current = ""

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current) + len(sent) + 1 <= self._chunk_size:
                current = f"{current} {sent}" if current else sent
            else:
                if current:
                    chunks.append(current.strip())
                current = sent

        if current.strip():
            chunks.append(current.strip())

        return chunks


class MarkdownChunker:
    """Split Markdown text by headings, preserving section structure."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self._chunk_size = chunk_size
        self._text_chunker = TextChunker(chunk_size, chunk_overlap)

    def split(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split Markdown by headings, then chunk large sections."""
        metadata = metadata or {}
        sections = self._split_by_headings(text)
        chunks: list[Chunk] = []

        for heading, content in sections:
            section_meta = dict(metadata)
            if heading:
                section_meta["heading"] = heading

            if len(content) <= self._chunk_size:
                if content.strip():
                    chunks.append(Chunk(content=content.strip(), metadata=section_meta))
            else:
                sub_chunks = self._text_chunker.split(content, section_meta)
                chunks.extend(sub_chunks)

        return chunks

    @staticmethod
    def _split_by_headings(text: str) -> list[tuple[str, str]]:
        """Split Markdown into (heading, content) pairs."""
        import re
        lines = text.split("\n")
        sections: list[tuple[str, str]] = []
        current_heading = ""
        current_lines: list[str] = []

        for line in lines:
            if re.match(r"^#{1,6}\s+", line):
                # Save previous section
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines)))
                current_heading = line.strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines)))

        return sections
