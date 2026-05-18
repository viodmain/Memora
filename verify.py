"""Manual verification script — shows inputs, outputs, and DB state at each step.

Usage: python verify.py
"""

import asyncio
from memora.config import load_config
from memora.storage import create_storage
from memora.llm import create_llm_client
from memora.memory.engine import MemoryEngineImpl
from memora.rag.engine import RAGEngineImpl
from memora.models.memory import Memory, MemoryType


def header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def show_db_state(storage):
    """Query and display current database state."""
    memories = await storage.db.fetch_all("SELECT id, content, memory_type, source, access_count FROM memories")
    documents = await storage.db.fetch_all("SELECT id, title, file_type, chunk_count FROM documents")
    chunks = await storage.db.fetch_all("SELECT id, document_id, chunk_index, substr(content,1,60) as preview FROM document_chunks")

    print(f"\n  [SQLite] memories: {len(memories)}")
    for m in memories:
        print(f"    {m['id'][:8]}... [{m['memory_type']}] {m['content'][:50]} (access={m['access_count']})")

    print(f"\n  [SQLite] documents: {len(documents)}")
    for d in documents:
        print(f"    {d['id'][:8]}... {d['title']} ({d['file_type']}, {d['chunk_count']} chunks)")

    print(f"\n  [SQLite] document_chunks: {len(chunks)}")
    for c in chunks:
        print(f"    {c['id']} [{c['chunk_index']}] {c['preview']}...")

    mem_vec_count = await storage.vector.count("memories")
    doc_vec_count = await storage.vector.count("documents")
    print(f"\n  [ChromaDB] memories vectors: {mem_vec_count}")
    print(f"  [ChromaDB] documents vectors: {doc_vec_count}")


async def main():
    cfg = load_config()

    # ── Setup ──
    header("SETUP")
    print(f"  LLM: {cfg.llm.provider} / {cfg.llm.model}")
    print(f"  Embedding: {cfg.embedding.provider} / {cfg.embedding.model}")

    llm = create_llm_client(
        base_url=cfg.llm.base_url,
        api_key=cfg.llm.api_key,
        model=cfg.llm.model,
        embedding_model=cfg.embedding.model,
        embedding_base_url=cfg.embedding.base_url,
        embedding_api_key=cfg.embedding.api_key,
    )
    storage = await create_storage(cfg.storage.db_path, cfg.storage.chroma_path)
    memory_engine = MemoryEngineImpl(storage, llm, dedup_threshold=cfg.memory_extraction.dedup_threshold)
    rag_engine = RAGEngineImpl(storage, llm, chunk_size=cfg.rag.chunk_size, chunk_overlap=cfg.rag.chunk_overlap)
    print("  OK")

    # ── 1. Manual memory save ──
    header("1. MANUAL MEMORY SAVE")
    m1 = Memory(content="User prefers Python for backend development", memory_type=MemoryType.PREFERENCE, source="manual")
    m2 = Memory(content="Project uses FastAPI as the web framework", memory_type=MemoryType.DECISION, source="manual")
    m3 = Memory(content="Deploy on Alibaba Cloud ECS with Docker", memory_type=MemoryType.FACT, source="manual")
    for m in [m1, m2, m3]:
        await memory_engine.save(m)
        print(f"  Saved: [{m.memory_type}] {m.content}")

    # ── 2. Memory recall ──
    header("2. MEMORY RECALL")
    query = "What backend framework does the project use?"
    print(f"  Query: \"{query}\"")
    results = await memory_engine.recall(query, top_k=3)
    print(f"  Results ({len(results)}):")
    for r in results:
        print(f"    [{r.memory_type}] {r.content}")

    # ── 3. Memory extraction from conversation ──
    header("3. MEMORY EXTRACTION FROM CONVERSATION")
    messages = [
        {"role": "user", "content": "We should use PostgreSQL for the database, and Redis for caching. Also I prefer dark mode in all my tools."},
        {"role": "assistant", "content": "Great choices! PostgreSQL is robust and Redis is perfect for caching."},
        {"role": "user", "content": "Let's deploy the staging environment on Friday."},
    ]
    print("  Input conversation:")
    for msg in messages:
        print(f"    {msg['role']}: {msg['content'][:60]}...")
    print("\n  Extracting...")
    extracted = await memory_engine.extract_from_messages(messages, source="conversation")
    print(f"  Extracted {len(extracted)} memories:")
    for e in extracted:
        print(f"    [{e.memory_type}] {e.content} (conf={e.confidence})")

    # ── 4. Document ingestion ──
    header("4. DOCUMENT INGESTION")
    import tempfile, os
    md_content = """# Memora Project

## Overview
Memora is a personal knowledge base application for LLM users.

## Architecture
The system uses FastAPI for the web API, SQLite for structured data,
and ChromaDB for vector storage.

## Installation
Run `pip install memora` to install the package.

## Usage
Use the CLI command `memora` to interact with the knowledge base.
You can ingest documents, search memories, and manage prompts.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(md_content)
        tmp_path = f.name

    print(f"  Ingesting: {tmp_path}")
    print(f"  Content preview:\n    {md_content[:100]}...")
    doc = await rag_engine.ingest(tmp_path)
    os.unlink(tmp_path)
    print(f"\n  Result: title={doc.title}, chunks={doc.chunk_count}, type={doc.file_type}")

    # ── 5. Document search ──
    header("5. DOCUMENT SEARCH")
    query = "How to install memora?"
    print(f"  Query: \"{query}\"")
    results = await rag_engine.search(query, top_k=3)
    print(f"  Results ({len(results)}):")
    for r in results:
        print(f"    [chunk {r.chunk_index}] {r.content[:80]}...")

    # ── 6. DB state ──
    header("6. DATABASE STATE")
    await show_db_state(storage)

    await storage.close()
    print(f"\n{'='*60}")
    print("  DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
