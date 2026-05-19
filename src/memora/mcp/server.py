"""MCP Server — exposes Memora tools to Claude Code and other MCP clients.

Uses FastMCP for a clean decorator-based API.
"""

from __future__ import annotations

from fastmcp import FastMCP

from memora.app import App
from memora.models.memory import Memory, MemoryType


def create_mcp_server(app: App) -> FastMCP:
    """Create FastMCP server with all Memora tools registered."""
    mcp = FastMCP(
        "memora",
        instructions="""You have access to Memora, a personal knowledge base. Follow these rules:

1. AUTO-EXTRACT: At the end of EVERY conversation, call `extract_and_save` with the conversation messages to save valuable information (technical decisions, user preferences, important facts, lessons learned).

2. AUTO-RECALL: At the start of a new conversation, if the user asks about previous work or context, call `recall` to search for relevant memories before responding.

3. OFFER INGEST: When the user shares or references a document, offer to ingest it with `ingest_document`.

4. SAVE IMPORTANT: During conversation, if you identify important information (decisions, preferences, facts), proactively call `save_memory` to record it.
""",
    )

    # ── Memory tools ──────────────────────────────────────────

    @mcp.tool()
    async def save_memory(content: str, memory_type: str, source: str = "claude_code") -> dict:
        """Save a single memory to the knowledge base."""
        memory = Memory(
            content=content,
            memory_type=MemoryType(memory_type),
            source=source,
        )
        result = await app.memory.save(memory)
        return result.model_dump()

    @mcp.tool()
    async def recall(query: str, top_k: int = 5, memory_type: str | None = None) -> list[dict]:
        """Search memories by semantic similarity."""
        mt = MemoryType(memory_type) if memory_type else None
        results = await app.memory.recall(query, top_k=top_k, memory_type=mt)
        return [r.model_dump() for r in results]

    @mcp.tool()
    async def extract_and_save(messages: list[dict]) -> list[dict]:
        """Extract memories from conversation and save them. Core auto-extraction tool."""
        results = await app.memory.extract_from_messages(messages)
        return [r.model_dump() for r in results]

    @mcp.tool()
    async def list_memories(memory_type: str | None = None, limit: int = 20) -> list[dict]:
        """List saved memories."""
        mt = MemoryType(memory_type) if memory_type else None
        results = await app.memory.list(memory_type=mt, limit=limit)
        return [r.model_dump() for r in results]

    # ── Knowledge tools ───────────────────────────────────────

    @mcp.tool()
    async def search_knowledge(query: str, top_k: int = 5) -> list[dict]:
        """Search document chunks by semantic similarity."""
        results = await app.rag.search(query, top_k=top_k)
        return [r.model_dump() for r in results]

    @mcp.tool()
    async def ingest_document(path_or_url: str) -> dict:
        """Ingest a document into the knowledge base."""
        result = await app.rag.ingest(path_or_url)
        return result.model_dump()

    # ── Prompt tools ──────────────────────────────────────────

    @mcp.tool()
    async def get_prompt(name: str) -> dict:
        """Get a prompt template's latest version."""
        prompt, version = await app.prompt.get(name)
        return {"prompt": prompt.model_dump(), "version": version.model_dump()}

    @mcp.tool()
    async def save_prompt(name: str, content: str, variables: list[str] | None = None) -> dict:
        """Save a prompt template (creates new version if exists)."""
        result = await app.prompt.save(name, content, variables=variables or [])
        return result.model_dump()

    # ── Search tools ──────────────────────────────────────────

    @mcp.tool()
    async def unified_search(query: str, scope: str = "all", top_k: int = 10) -> list[dict]:
        """Search across memories, documents, and prompts."""
        results = await app.search.search(query, scope=scope, top_k=top_k)
        return [r.model_dump() for r in results]

    # ── Stats ─────────────────────────────────────────────────

    @mcp.tool()
    async def get_stats() -> dict:
        """Get knowledge base statistics."""
        mem_count = await app.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM memories")
        doc_count = await app.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM documents")
        prompt_count = await app.storage.db.fetch_one("SELECT COUNT(*) as cnt FROM prompts")
        return {
            "memories": mem_count["cnt"] if mem_count else 0,
            "documents": doc_count["cnt"] if doc_count else 0,
            "prompts": prompt_count["cnt"] if prompt_count else 0,
        }

    return mcp
