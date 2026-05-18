# Memora

Personal knowledge base for LLM users with MCP auto-memory extraction.

## Features

- **Memory Engine** — Extract, store, and recall conversation memories automatically
- **RAG Engine** — Ingest documents (Markdown, text, code) and search by semantic similarity
- **Prompt Engine** — Version-manage prompts with scoring and optimization
- **MCP Server** — Auto-extract memories during Claude Code conversations
- **Multi-provider** — Supports MiMo, DashScope, OpenAI, DeepSeek, Ollama, or any OpenAI-compatible API

## Install

```bash
git clone https://github.com/viodmain/Memora.git
cd Memora
pip install -e .
```

## Configure

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Chat LLM (OpenAI-compatible)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1

# Embedding (DashScope)
DASHSCOPE_API_KEY=sk-xxx
```

Default model is `mimo-v2.5-pro`. Change in `config/settings.yaml`:

```yaml
llm:
  model: "gpt-4o"           # or qwen-plus, deepseek-chat, etc.
  base_url: "${OPENAI_BASE_URL}"
  api_key: "${OPENAI_API_KEY}"
```

## Usage

### CLI

```bash
memora ingest ./docs/api.md      # Ingest a document
memora search "how to install"   # Unified search
memora memory add "fact" -c "..."  # Add memory
memora memory list               # List memories
memora prompt list               # List prompts
memora stats                     # Show statistics
```

### REST API

```bash
uvicorn memora.api.app:app --reload --port 8000
```

Endpoints:
- `GET /api/memory/recall?query=xxx` — Search memories
- `POST /api/memory/save` — Save memory
- `GET /api/knowledge/search?query=xxx` — Search documents
- `POST /api/knowledge/ingest?path=xxx` — Ingest document
- `GET /api/search/?query=xxx` — Unified search

### Web Frontend

```bash
cd web
npm install
npm run dev
```

Opens at http://localhost:5173

### MCP Server (Claude Code integration)

```bash
# Add to Claude Code
claude mcp add memora python -m memora.mcp --cwd /path/to/Memora
```

Or add to `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "memora": {
      "command": "python",
      "args": ["-m", "memora.mcp"],
      "cwd": "/path/to/Memora"
    }
  }
}
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

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
