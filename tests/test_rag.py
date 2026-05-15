"""Tests for RAG engine, chunker, and loaders."""

import pytest
import pytest_asyncio
from pathlib import Path

from memora.rag import RAGEngine
from memora.rag.engine import RAGEngineImpl
from memora.rag.chunker import TextChunker, MarkdownChunker
from memora.rag.loaders import LoaderRegistry, create_default_registry
from memora.rag.loaders.markdown import MarkdownLoader
from memora.rag.loaders.text import TextLoader
from memora.models.document import Document, DocumentChunk
from memora.storage import Storage
from memora.llm import ExtractedMemory


# ── Stub LLM ─────────────────────────────────────────────────

class StubLLM:
    """Minimal LLM stub for RAG tests."""

    def __init__(self):
        self.embed_calls: list[str] = []
        self._embed_dim = 8

    async def chat(self, messages, temperature=0.7):
        return ""

    async def extract_memories(self, messages):
        return []

    async def embed(self, text):
        self.embed_calls.append(text)
        vec = [0.0] * self._embed_dim
        for i, ch in enumerate(text[:self._embed_dim]):
            vec[i] = (ord(ch) % 100) / 100.0
        return vec

    async def embed_batch(self, texts):
        return [await self.embed(t) for t in texts]


# ── Fixtures ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def rag_engine(tmp_path) -> tuple[RAGEngineImpl, StubLLM]:
    """Create a RAGEngineImpl with stub LLM and temp storage."""
    from memora.storage import create_storage

    storage = await create_storage(
        str(tmp_path / "test.db"),
        str(tmp_path / "chroma"),
    )
    llm = StubLLM()
    eng = RAGEngineImpl(storage, llm, chunk_size=200, chunk_overlap=20)
    yield eng, llm
    await storage.close()


@pytest.fixture
def sample_markdown(tmp_path) -> Path:
    """Create a sample Markdown file for testing."""
    content = """# Introduction

This is the introduction section. It provides an overview of the project.

## Installation

Run the following command to install:

    pip install memora

## Usage

After installation, you can use the CLI:

    memora ingest ./docs
    memora search "how to install"
"""
    path = tmp_path / "sample.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_text(tmp_path) -> Path:
    """Create a sample text file for testing."""
    content = "Hello world. " * 50  # Long enough to need chunking
    path = tmp_path / "sample.txt"
    path.write_text(content, encoding="utf-8")
    return path


# ── Chunker Tests ────────────────────────────────────────────

class TestTextChunker:
    def test_split_short_text(self):
        chunker = TextChunker(chunk_size=1000)
        chunks = chunker.split("Hello world")
        assert len(chunks) == 1
        assert chunks[0].content == "Hello world"

    def test_split_long_text(self):
        text = "word " * 200  # ~1000 chars
        chunker = TextChunker(chunk_size=200, chunk_overlap=20)
        chunks = chunker.split(text)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c.content) <= 250  # some tolerance

    def test_split_empty_text(self):
        chunker = TextChunker()
        assert chunker.split("") == []
        assert chunker.split("   ") == []

    def test_split_preserves_metadata(self):
        chunker = TextChunker(chunk_size=50)
        chunks = chunker.split("Hello world. " * 10, metadata={"source": "test"})
        for c in chunks:
            assert c.metadata["source"] == "test"

    def test_split_by_paragraphs(self):
        chunker = TextChunker(chunk_size=100)
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = chunker.split(text)
        assert len(chunks) >= 1


class TestMarkdownChunker:
    def test_split_by_headings(self):
        chunker = MarkdownChunker(chunk_size=1000)
        text = "# Title\n\nIntro text.\n\n## Section 1\n\nContent 1.\n\n## Section 2\n\nContent 2."
        chunks = chunker.split(text)
        assert len(chunks) >= 2
        headings = [c.metadata.get("heading") for c in chunks]
        assert any("Section 1" in h for h in headings if h)
        assert any("Section 2" in h for h in headings if h)

    def test_split_large_section(self):
        chunker = MarkdownChunker(chunk_size=50)
        text = "# Big Section\n\n" + "word " * 100
        chunks = chunker.split(text)
        assert len(chunks) > 1

    def test_split_preserves_heading_metadata(self):
        chunker = MarkdownChunker(chunk_size=1000)
        text = "# My Heading\n\nSome content here."
        chunks = chunker.split(text)
        assert any(c.metadata.get("heading") == "# My Heading" for c in chunks)


# ── Loader Tests ─────────────────────────────────────────────

class TestMarkdownLoader:
    def test_can_load_markdown(self):
        loader = MarkdownLoader()
        assert loader.can_load("test.md") is True
        assert loader.can_load("test.markdown") is True
        assert loader.can_load("test.txt") is False

    @pytest.mark.asyncio
    async def test_load_markdown(self, sample_markdown):
        loader = MarkdownLoader()
        result = await loader.load(str(sample_markdown))
        assert "Introduction" in result.content
        assert result.metadata["file_type"] == "md"
        assert result.metadata["title"] == "sample"


class TestTextLoader:
    def test_can_load_text(self):
        loader = TextLoader()
        assert loader.can_load("test.txt") is True
        assert loader.can_load("test.py") is True
        assert loader.can_load("test.json") is True
        assert loader.can_load("test.md") is False

    @pytest.mark.asyncio
    async def test_load_text(self, sample_text):
        loader = TextLoader()
        result = await loader.load(str(sample_text))
        assert "Hello world" in result.content
        assert result.metadata["file_type"] == "txt"


class TestLoaderRegistry:
    def test_selects_markdown_loader(self):
        registry = create_default_registry()
        loader = registry.get_loader("test.md")
        assert isinstance(loader, MarkdownLoader)

    def test_selects_text_loader(self):
        registry = create_default_registry()
        loader = registry.get_loader("test.py")
        assert isinstance(loader, TextLoader)

    def test_raises_for_unknown(self):
        registry = create_default_registry()
        with pytest.raises(ValueError, match="No loader found"):
            registry.get_loader("test.pdf")


# ── RAG Engine Tests ─────────────────────────────────────────

class TestRAGEngineProtocol:
    @pytest.mark.asyncio
    async def test_satisfies_protocol(self, rag_engine):
        eng, _ = rag_engine
        assert isinstance(eng, RAGEngine)


class TestIngest:
    @pytest.mark.asyncio
    async def test_ingest_markdown(self, rag_engine, sample_markdown):
        eng, llm = rag_engine
        doc = await eng.ingest(str(sample_markdown))

        assert isinstance(doc, Document)
        assert doc.title == "sample"
        assert doc.file_type == "md"
        assert doc.chunk_count > 0
        assert len(llm.embed_calls) == doc.chunk_count

    @pytest.mark.asyncio
    async def test_ingest_text(self, rag_engine, sample_text):
        eng, _ = rag_engine
        doc = await eng.ingest(str(sample_text))

        assert doc.chunk_count > 0
        assert doc.file_type == "txt"

    @pytest.mark.asyncio
    async def test_ingest_stores_in_db(self, rag_engine, sample_markdown):
        eng, _ = rag_engine
        doc = await eng.ingest(str(sample_markdown))

        # Verify document in SQLite
        fetched = await eng.get_document(doc.id)
        assert fetched is not None
        assert fetched.title == "sample"

        # Verify chunks in SQLite
        chunks = await rag_engine[0]._storage.db.fetch_all(
            "SELECT * FROM document_chunks WHERE document_id = ?", (doc.id,)
        )
        assert len(chunks) == doc.chunk_count

    @pytest.mark.asyncio
    async def test_ingest_unsupported_file(self, rag_engine, tmp_path):
        eng, _ = rag_engine
        path = tmp_path / "test.pdf"
        path.write_bytes(b"fake pdf")
        with pytest.raises(ValueError, match="No loader found"):
            await eng.ingest(str(path))


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_chunks(self, rag_engine, sample_markdown):
        eng, _ = rag_engine
        await eng.ingest(str(sample_markdown))

        results = await eng.search("installation", top_k=3)
        assert len(results) > 0
        assert all(isinstance(c, DocumentChunk) for c in results)

    @pytest.mark.asyncio
    async def test_search_with_document_filter(self, rag_engine, sample_markdown):
        eng, _ = rag_engine
        doc = await eng.ingest(str(sample_markdown))

        results = await eng.search("usage", top_k=5, document_id=doc.id)
        assert all(c.document_id == doc.id for c in results)

    @pytest.mark.asyncio
    async def test_search_empty_when_no_docs(self, rag_engine):
        eng, _ = rag_engine
        results = await eng.search("anything")
        assert results == []


class TestDocumentManagement:
    @pytest.mark.asyncio
    async def test_list_documents(self, rag_engine, sample_markdown):
        eng, _ = rag_engine
        await eng.ingest(str(sample_markdown))

        docs = await eng.list_documents()
        assert len(docs) == 1
        assert docs[0].title == "sample"

    @pytest.mark.asyncio
    async def test_delete_document(self, rag_engine, sample_markdown):
        eng, _ = rag_engine
        doc = await eng.ingest(str(sample_markdown))

        result = await eng.delete_document(doc.id)
        assert result is True
        assert await eng.get_document(doc.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, rag_engine):
        eng, _ = rag_engine
        result = await eng.delete_document("nonexistent")
        assert result is False
