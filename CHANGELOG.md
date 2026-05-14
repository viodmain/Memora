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
