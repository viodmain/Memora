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
