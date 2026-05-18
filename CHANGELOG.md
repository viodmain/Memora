# Memora 开发日志

## 2026-05-12

- 初始化 git 仓库，配置 .gitignore
- 完成《项目规划与技术选型》文档
- 完成《开发计划书》，定义模块接口、依赖注入、数据库 Schema、8 个里程碑
- 安装项目依赖：fastapi, langchain, langchain-openai, langchain-text-splitters, chromadb, aiosqlite, pypdf2

## 2026-05-13

### Milestone 1: Basic Framework (complete)

- M1.1: Project skeleton — pyproject.toml, directory structure, all __init__.py
- M1.2: Config loading — config.py + settings.yaml, env var resolution
- M1.3: Data models — Memory, Document, Prompt, SearchResult (Pydantic)
- M1.4: SQLite storage — database.py + migrations.py, 8 tables with indexes
- M1.5: Vector storage — ChromaDB wrapper with upsert/search/delete/count
- M1.6: Storage facade — unified Storage dataclass + create_storage() factory
- Prompt templates: memory_extract, memory_summarize, rag_query, prompt_optimize
- Verified: all imports, config loading, SQLite + ChromaDB integration test passed
- Tests: 34 tests written (test_config, test_models, test_storage), all passing
- Bugfix: enable SQLite PRAGMA foreign_keys for cascade delete
- Bugfix: ChromaDB rejects empty metadata dict, use None instead

### Milestone 2: LLM Client (complete)

- M2.1: LLMClient Protocol — chat, extract_memories, embed, embed_batch
- M2.2: DashScopeLLM implementation via langchain-openai (OpenAI-compatible)
- M2.3: Memory extraction — JSON parsing with markdown code block handling, type validation
- M2.4: PromptTemplate — YAML template loading with variable substitution and caching
- Factory: create_llm_client() wires config to LLM instance
- Protocol conformance: DashScopeLLM satisfies LLMClient Protocol
- Tests: 17 new tests (test_llm.py), 51 total, all passing

## 2026-05-14

### Milestone 3: Memory Engine (complete)

- M3.1: MemoryEngine Protocol — 8 methods (save/get/list/update/delete/extract/recall/summarize)
- M3.2: MemoryEngineImpl CRUD — SQLite + ChromaDB dual-write, access_count tracking
- M3.3: extract_from_messages — LLM extraction + vector dedup (threshold 0.9)
- M3.4: recall — embed query → ChromaDB vector search → fetch full records
- M3.5: summarize_conversation — prompt template + JSON parsing
- Bugfix: add `from __future__ import annotations` for Protocol type hints
- Bugfix: get() increments access_count before reading (was returning stale count)
- Tests: 18 new tests (test_memory.py), 69 total, all passing

### Multi-provider support (complete)

- Config: added EmbeddingConfig — separate embedding provider (DashScope) from chat provider (MiMo)
- LLM: embedding uses DashScope SDK directly (langchain-openai incompatible with DashScope embedding API)
- VectorStore: added upsert_texts/search_text for ChromaDB built-in embedding (unused for now, ready for offline mode)
- Manual test: MiMo chat + DashScope embedding dual-engine verified end-to-end
- Installed: dashscope SDK, sentence-transformers (disk full, deferred)

## 2026-05-15

### Milestone 4: RAG Engine (core complete)

- M4.1: RAGEngine Protocol — ingest, search, list_documents, get_document, delete_document
- M4.2: MarkdownLoader — loads .md/.markdown/.mdx files
- M4.3: TextChunker + MarkdownChunker — paragraph splitting, sentence fallback, heading-based splitting
- M4.4: RAGEngineImpl ingest pipeline — load → chunk → embed_batch → store (SQLite + ChromaDB)
- M4.5: RAG search — embed query → ChromaDB vector search → fetch chunk records
- M4.6: TextLoader — fallback for .txt/.py/.js/.json/.yaml etc.
- LoaderRegistry — extensible loader system with auto-detection
- Bugfix: chunker now splits continuous text without sentence breaks (word-level fallback)
- Tests: 26 new tests (test_rag.py), 95 total, all passing
- P1 deferred: PDF, webpage, code loaders

### Milestone 5: Prompt Engine (complete)

- M5.1: PromptEngine Protocol — save/get/list/score/compare/optimize/delete
- M5.2: PromptEngineImpl CRUD — SQLite storage with JSON variables
- M5.3: Version management — auto-increment, all versions preserved
- M5.4: score (1-5 validation), compare (diff two versions), optimize (LLM suggestions)
- Tests: 17 new tests (test_prompt.py), 112 total, all passing

### Milestone 6: Search + MCP Server (complete)

- M6.1: SearchService — unified search across memory, documents, prompts (async parallel)
- M6.2: MCP Server via FastMCP — 10 tools registered (save_memory, recall, extract_and_save, list_memories, search_knowledge, ingest_document, get_prompt, save_prompt, unified_search, get_stats)
- M6.3: App container — create_app() factory with dependency injection
- Tests: 5 new tests (test_search.py), 117 total, all passing

### Milestone 7: CLI + API (complete)

- M7.1: CLI (Typer + Rich) — ingest, search, memory (list/add/delete/recall), prompt, stats, serve
- M7.2: CLI /prompt — list/add/get/score actions
- M7.3: FastAPI routes — /api/memory, /api/knowledge, /api/prompt, /api/search
- Bugfix: FastAPI deprecation warning (regex → pattern)
- Tests: 8 new tests (test_api.py), 125 total, all passing

### Milestone 8: Testing + Export (complete)

- M8.1: Data export — export_memories_json/csv, export_documents_json, export_all_json
- M8.2: Integration tests — memory lifecycle, RAG lifecycle, prompt versioning, unified search
- M8.3: Final cleanup
- Tests: 11 new tests (test_exporter + test_integration), 136 total, all passing

### Phase 1 MVP: complete (all 8 milestones)

## 2026-05-16

### Phase 2: Web Frontend (core complete)

- Vue 3 + TypeScript + Vite project setup
- vue-router for SPA navigation, axios for API calls
- Vite proxy config for API requests to FastAPI backend
- Dashboard page — stats overview, recent memories
- Memory page — browse, search (recall), add, delete
- Knowledge page — document list, ingest, semantic search
- Prompt page — list, view versions, add, delete
- Navigation bar with 4 sections
- Build passes TypeScript check + Vite production build
- .mcp.json — MCP Server configuration for Claude Code integration

### Phase 3: Enhanced Features (complete)

- P3.1: Memory decay — list(sort_by="relevance") ranks by access_count + recency
- P3.2: Auto-organize — removes exact duplicates and stale memories (30 days, 0 access)
- P3.3: API Key auth — X-API-Key header, MEMORA_API_KEY env var (disabled if not set)
- Tests: 9 new tests (test_enhanced.py), 145 total, all passing

### Phase 4: Release Prep (complete)

- README — install, configure, CLI/API/Web/MCP usage guide
- .env.example — dual-engine config (chat + embedding)
- pyproject.toml — pip install ready
- USAGE.md — detailed usage guide (CLI/API/Web/MCP)

## 2026-05-18

### Bugfixes & MCP Integration

- fix: add __main__.py to cli package (python -m memora.cli works)
- fix: add dashscope and fastmcp to pyproject.toml dependencies
- feat: SSE transport mode for MCP server (python -m memora.mcp --sse)
- Claude Code MCP integration verified — 10 tools connected
- Rebuilt wheel package with all fixes

### TODO

- [ ] Auto-extract: configure Claude Code hook or system prompt to automatically extract memories at end of conversation
- [ ] PyPI publish: publish to PyPI for direct pip install
- [ ] PDF/Code loaders: add PDF, code file, and webpage loaders (P1 deferred from Phase 1)
- [ ] Bundle web frontend: build Vue static files into Python wheel, serve from FastAPI (single pip install)
