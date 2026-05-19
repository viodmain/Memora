# Memora 使用指南

## 安装

### 方式一：从源码安装（推荐）

```bash
git clone https://github.com/viodmain/Memora.git
cd Memora
pip install -e .
```

### 方式二：从 wheel 安装

```bash
pip install memora-0.1.0-py3-none-any.whl
```

### 安装前端（可选）

```bash
cd web
npm install
```

---

## 配置

### 1. API Key 配置

**`.env` 文件位置**：放在你运行命令的工作目录下。

```powershell
# 示例：你想在 D:\MyKnowledge 下使用 memora
cd D:\MyKnowledge
# 把 .env 文件放在这个目录下
```

**方式一：`.env` 文件（推荐）**

复制环境变量模板到你的工作目录：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```env
# Chat LLM（对话用，OpenAI 兼容接口）
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1

# Embedding（向量化用，DashScope）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

**方式二：系统环境变量（不用 .env 文件）**

```powershell
# PowerShell 临时设置（当前终端有效）
$env:OPENAI_API_KEY="sk-xxx"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:DASHSCOPE_API_KEY="sk-xxx"

# 或加到系统环境变量（永久生效）
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-xxx", "User")
```

### 2. 模型配置

编辑 `config/settings.yaml`，修改 LLM 提供商和模型：

```yaml
llm:
  provider: "openai"                    # 提供商标识
  base_url: "${OPENAI_BASE_URL}"        # API 地址（从 .env 读取）
  api_key: "${OPENAI_API_KEY}"          # API Key（从 .env 读取）
  model: "gpt-4o"                       # 模型名称

embedding:
  provider: "dashscope"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "${DASHSCOPE_API_KEY}"
  model: "text-embedding-v3"
```

**常用 LLM 配置：**

```yaml
# OpenAI
llm:
  base_url: "https://api.openai.com/v1"
  model: "gpt-4o"

# DashScope（阿里百炼）
llm:
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-plus"

# DeepSeek
llm:
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"

# 本地 Ollama
llm:
  base_url: "http://localhost:11434/v1"
  model: "qwen2.5"
```

### 3. 存储配置

```yaml
storage:
  db_path: "data/memora.db"       # SQLite 数据库路径
  chroma_path: "data/chroma"      # ChromaDB 向量数据路径
```

### 4. API 认证（可选）

如需保护 REST API，在 `.env` 中添加：

```env
MEMORA_API_KEY=your-secret-key
```

客户端请求时需携带 Header：`X-API-Key: your-secret-key`

---

## 服务说明

Memora 有两个独立服务，按需启动：

| 服务 | 命令 | 用途 |
|---|---|---|
| REST API + Web | `python -m uvicorn memora.api.app:app --port 8000` | Web 界面、API 调用 |
| MCP Server | `python -m memora.mcp --sse --port 8765` | Claude Code 集成 |

两个服务可以同时运行（各开一个终端），也可以只启动其中一个。

---

## 使用方式

### 方式一：CLI 命令行

```bash
# 摄入文档
memora ingest ./docs/api.md

# 统一搜索（搜索记忆 + 文档 + Prompt）
memora search "如何配置认证"

# 记忆管理
memora memory list                          # 列出所有记忆
memora memory add -c "用户偏好 Python" -t preference  # 添加记忆
memora memory recall -q "技术栈"             # 语义搜索记忆
memora memory delete <memory-id>            # 删除记忆

# Prompt 管理
memora prompt list                          # 列出所有 Prompt
memora prompt add -n "代码审查" -c "你是一个代码审查专家..."
memora prompt get -n "代码审查"              # 查看 Prompt
memora prompt score -n "代码审查" -v 1 -s 4.5  # 评分

# 统计信息
memora stats
```

### 方式二：REST API

启动 API 服务：

```bash
uvicorn memora.api.app:app --reload --port 8000
```

**记忆接口：**

```bash
# 保存记忆
curl -X POST http://localhost:8000/api/memory/save \
  -H "Content-Type: application/json" \
  -d '{"content": "项目用 FastAPI", "memory_type": "decision"}'

# 语义搜索记忆
curl "http://localhost:8000/api/memory/recall?query=框架&top_k=5"

# 从对话提取记忆
curl -X POST http://localhost:8000/api/memory/extract \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "我喜欢 Python"}]}'

# 列出记忆
curl "http://localhost:8000/api/memory/?limit=20"
```

**知识库接口：**

```bash
# 摄入文档
curl -X POST "http://localhost:8000/api/knowledge/ingest?path=./docs/api.md"

# 搜索文档
curl "http://localhost:8000/api/knowledge/search?query=安装"

# 列出文档
curl "http://localhost:8000/api/knowledge/documents"
```

**统一搜索：**

```bash
curl "http://localhost:8000/api/search/?query=Python&scope=all&top_k=10"
```

### 方式三：Web 前端

```bash
# 终端 1：启动 API
uvicorn memora.api.app:app --reload --port 8000

# 终端 2：启动前端
cd web && npm run dev
```

浏览器打开 http://localhost:5173

### 方式四：MCP Server（Claude Code 集成）

```bash
# 添加到 Claude Code
claude mcp add memora python -m memora.mcp --cwd /path/to/Memora
```

或在项目根目录创建 `.mcp.json`：

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

重启 Claude Code 后，AI 会自动获得以下能力：
- 对话结束时自动提取记忆
- 新对话开始时自动召回相关记忆
- 摄入文档到知识库
- 搜索知识库

---

## MCP 工具列表

| 工具 | 功能 |
|---|---|
| `save_memory` | 保存单条记忆 |
| `recall` | 语义搜索记忆 |
| `extract_and_save` | 从对话批量提取记忆 |
| `list_memories` | 列出记忆 |
| `search_knowledge` | 搜索文档 |
| `ingest_document` | 摄入文档 |
| `get_prompt` | 获取 Prompt |
| `save_prompt` | 保存 Prompt |
| `unified_search` | 统一搜索 |
| `get_stats` | 获取统计信息 |

---

## 数据目录

```
data/
├── memora.db      # SQLite 数据库（记忆、文档、Prompt 元数据）
├── chroma/        # ChromaDB 向量数据（语义搜索用）
└── documents/     # 原始文档存储（可选）
```

备份数据：复制整个 `data/` 目录即可。

---

## 常见问题

**Q: embedding 和 chat 可以用同一个 API 吗？**

可以。如果 LLM 提供商同时支持 embedding（如 OpenAI、DashScope），在 `config/settings.yaml` 中把 `embedding` 的 `base_url` 和 `api_key` 改成和 `llm` 一样即可。

**Q: 没有 DashScope API Key 怎么办？**

修改 `config/settings.yaml`，把 embedding 也改成你有的 LLM 提供商：

```yaml
embedding:
  provider: "openai"
  base_url: "${OPENAI_BASE_URL}"
  api_key: "${OPENAI_API_KEY}"
  model: "text-embedding-3-small"
```

**Q: 数据存在哪里？会丢失吗？**

数据存在项目目录的 `data/` 下，SQLite 和 ChromaDB 都是本地文件。只要不删除 `data/` 目录，数据不会丢失。

**Q: 如何清空数据重新开始？**

```bash
rm -rf data/
```
