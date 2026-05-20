# Memora Usage Guide

## Install

### Option 1: From source (recommended)

```bash
git clone https://github.com/viodmain/Memora.git
cd Memora
pip install -e .
```

### Option 2: From wheel

```bash
pip install memora-0.1.0-py3-none-any.whl
```

### Install frontend (optional)

```bash
cd web
npm install
```

---

## Configuration

### 1. API Key Setup

**Recommended: System environment variables (persistent, works with MCP Server)**

```powershell
# Windows PowerShell
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-key", "User")
[System.Environment]::SetEnvironmentVariable("OPENAI_BASE_URL", "https://api.openai.com/v1", "User")
[System.Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "your-dashscope-key", "User")
```

```bash
# Linux / macOS (add to ~/.bashrc or ~/.zshrc)
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export DASHSCOPE_API_KEY="your-dashscope-key"
```

Restart terminal after setting.

**Alternative: `.env` file (CLI only, not recommended for MCP Server)**

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Model Configuration

Edit `config/settings.yaml` to change the LLM provider and model:

```yaml
llm:
  provider: "openai"
  base_url: "${OPENAI_BASE_URL}"
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4o"

embedding:
  provider: "dashscope"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "${DASHSCOPE_API_KEY}"
  model: "text-embedding-v3"
```

**Common LLM configurations:**

```yaml
# OpenAI
llm:
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"

# DashScope (Alibaba)
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-plus"

# DeepSeek
llm:
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"

# Local Ollama
llm:
  base_url: "http://localhost:11434/v1"
  model: "qwen2.5"
```

### 3. Storage Configuration

```yaml
storage:
  db_path: "data/memora.db"       # SQLite database path
  chroma_path: "data/chroma"      # ChromaDB vector data path
```

### 4. API Authentication (optional)

To protect the REST API, add to `.env`:

```env
MEMORA_API_KEY=your-secret-key
```

Clients must include header: `X-API-Key: your-secret-key`

---

## Services

Memora has two independent services — start whichever you need:

| Service | Command | Purpose |
|---|---|---|
| REST API + Web | `python -m uvicorn memora.api.app:app --port 8000` | Web UI, API calls |
| MCP Server | `python -m memora.mcp --sse --port 8765` | Claude Code integration |

Both can run simultaneously (separate terminals), or you can start just one.

---

## Usage

### Option 1: CLI

```bash
# Ingest a document
memora ingest ./docs/api.md

# Unified search (search memory + documents + prompts)
memora search "how to configure authentication"

# Memory management
memora memory list                          # List all memories
memora memory add -c "User prefers Python" -t preference  # Add memory
memora memory recall -q "tech stack"        # Semantic search
memora memory delete <memory-id>            # Delete memory

# Prompt management
memora prompt list                          # List all prompts
memora prompt add -n "code review" -c "You are a code reviewer..."
memora prompt get -n "code review"          # View prompt
memora prompt score -n "code review" -v 1 -s 4.5  # Rate

# Statistics
memora stats
```

### Option 2: REST API

Start the API server:

```bash
uvicorn memora.api.app:app --reload --port 8000
```

**Memory endpoints:**

```bash
# Save memory
curl -X POST http://localhost:8000/api/memory/save \
  -H "Content-Type: application/json" \
  -d '{"content": "Project uses FastAPI", "memory_type": "decision"}'

# Semantic search memories
curl "http://localhost:8000/api/memory/recall?query=framework&top_k=5"

# Extract memories from conversation
curl -X POST http://localhost:8000/api/memory/extract \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I like Python"}]}'

# List memories
curl "http://localhost:8000/api/memory/?limit=20"
```

**Knowledge endpoints:**

```bash
# Ingest document
curl -X POST "http://localhost:8000/api/knowledge/ingest?path=./docs/api.md"

# Search documents
curl "http://localhost:8000/api/knowledge/search?query=installation"

# List documents
curl "http://localhost:8000/api/knowledge/documents"
```

**Unified search:**

```bash
curl "http://localhost:8000/api/search/?query=Python&scope=all&top_k=10"
```

### Option 3: Web Frontend

```bash
# Terminal 1: Start API
uvicorn memora.api.app:app --reload --port 8000

# Terminal 2: Start frontend
cd web && npm run dev
```

Open http://localhost:5173 in browser.

### Option 4: MCP Server (Claude Code integration)

```bash
# Add to Claude Code
claude mcp add memora --transport sse http://127.0.0.1:8765/sse
```

Start MCP server in a separate terminal:

```bash
python -m memora.mcp --sse --port 8765
```

Or add `.mcp.json` to your project:

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

After restarting Claude Code, the AI automatically gains:
- Auto-extract memories at end of conversation
- Auto-recall related memories in new conversations
- Ingest documents into knowledge base
- Search knowledge base

---

## MCP Tools

| Tool | Function |
|---|---|
| `save_memory` | Save a single memory |
| `recall` | Semantic search memories |
| `extract_and_save` | Batch-extract memories from conversation |
| `list_memories` | List memories |
| `search_knowledge` | Search documents |
| `ingest_document` | Ingest document |
| `get_prompt` | Get prompt template |
| `save_prompt` | Save prompt template |
| `unified_search` | Unified search |
| `get_stats` | Get statistics |

---

## Data Directory

```
data/
├── memora.db      # SQLite database (memories, documents, prompts metadata)
├── chroma/        # ChromaDB vector data (for semantic search)
└── documents/     # Raw document storage (optional)
```

Backup: Copy the entire `data/` directory.

---

## FAQ

**Q: Can embedding and chat use the same API?**

Yes. If your LLM provider supports embedding (e.g., OpenAI, DashScope), update the `embedding` section in `config/settings.yaml` to match the `llm` section.

**Q: No DashScope API Key?**

Update `config/settings.yaml` to use your available provider for embedding:

```yaml
embedding:
  provider: "openai"
  base_url: "${OPENAI_BASE_URL}"
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"
```

**Q: Where is the data stored?**

Data is stored in `data/` under your working directory. Both SQLite and ChromaDB are local files. As long as you don't delete `data/`, your data is safe.

**Q: How to clear all data and start fresh?**

```bash
rm -rf data/
```
