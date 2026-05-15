# Memora

Personal knowledge base for LLM users with MCP auto-memory extraction.

## Features

- **Memory Engine** — Extract, store, and recall conversation memories automatically
- **RAG Engine** — Ingest documents (Markdown, text, code) and search by semantic similarity
- **Prompt Engine** — Version-manage prompts with scoring and optimization
- **MCP Server** — Auto-extract memories during Claude Code conversations (coming soon)
- **Multi-provider** — Supports MiMo, DashScope, OpenAI, DeepSeek, Ollama, or any OpenAI-compatible API

## Quick Start

### Install

```bash
git clone https://github.com/yourname/memora.git
cd memora
pip install -e .
```

### Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
# CLI
memora

# MCP Server (for Claude Code integration)
memora mcp serve

# Web API
uvicorn memora.api.app:app --reload
```

## Architecture

```
┌─────────────┐  ┌──────────────┐  ┌─────────────┐
│  CLI (Typer) │  │  Web (Vue 3) │  │  MCP Server │
└──────┬───────┘  └──────┬───────┘  └──────┬──────┘
       └─────────────────┼─────────────────┘
                         ▼
              ┌──────────────────┐
              │   Engines Layer   │
              │  Memory | RAG | Prompt | Search │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │   Storage Layer   │
              │  SQLite + ChromaDB │
              └──────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | MiMo / DashScope / OpenAI-compatible |
| Embedding | DashScope text-embedding-v3 |
| Framework | LangChain |
| Vector DB | ChromaDB |
| Relation DB | SQLite + aiosqlite |
| Web API | FastAPI |
| CLI | Typer + Rich |

## Project Structure

```
src/memora/
├── models/          # Pydantic data models
├── storage/         # SQLite + ChromaDB storage layer
├── llm.py           # LLM client (Protocol + DashScope impl)
├── memory/          # Memory engine (extract, recall, summarize)
├── rag/             # RAG engine (ingest, chunk, search)
├── prompt/          # Prompt engine (CRUD, versioning, scoring)
├── search/          # Unified search service
├── mcp/             # MCP Server
├── cli/             # CLI entry point
├── api/             # FastAPI routes
└── config.py        # Configuration loader
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific module tests
pytest tests/test_memory.py -v
pytest tests/test_rag.py -v
pytest tests/test_prompt.py -v
```

## License

MIT
