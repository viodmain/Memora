"""Memory engine — implementation."""

from __future__ import annotations

import json
from datetime import datetime

from memora.models.memory import Memory, MemoryType, ConversationSummary
from memora.storage import Storage
from memora.storage.vector_store import VectorRecord
from memora.llm import LLMClient


class MemoryEngineImpl:
    """Concrete implementation of the MemoryEngine Protocol."""

    def __init__(self, storage: Storage, llm: LLMClient, dedup_threshold: float = 0.9) -> None:
        self._storage = storage
        self._llm = llm
        self._dedup_threshold = dedup_threshold

    # ── CRUD ──────────────────────────────────────────────────

    async def save(self, memory: Memory) -> Memory:
        """Write memory to SQLite and vectorize into ChromaDB."""
        memory.updated_at = datetime.now()
        await self._storage.db.execute(
            "INSERT INTO memories (id, content, memory_type, source, confidence, tags, access_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                memory.id,
                memory.content,
                memory.memory_type.value,
                memory.source,
                memory.confidence,
                ",".join(memory.tags),
                memory.access_count,
                memory.created_at.isoformat(),
                memory.updated_at.isoformat(),
            ),
        )
        embedding = await self._llm.embed(memory.content)
        await self._storage.vector.upsert("memories", [
            VectorRecord(
                id=memory.id,
                embedding=embedding,
                metadata={"type": memory.memory_type.value},
            )
        ])
        return memory

    async def get(self, memory_id: str) -> Memory | None:
        """Fetch a single memory by ID, incrementing access count."""
        await self._storage.db.execute(
            "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
            (memory_id,),
        )
        row = await self._storage.db.fetch_one(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        if row is None:
            return None
        return self._row_to_memory(row)

    async def list(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Memory]:
        """List memories with optional type filter, ordered by created_at DESC."""
        if memory_type:
            rows = await self._storage.db.fetch_all(
                "SELECT * FROM memories WHERE memory_type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (memory_type.value, limit, offset),
            )
        else:
            rows = await self._storage.db.fetch_all(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [self._row_to_memory(r) for r in rows]

    async def update(self, memory: Memory) -> Memory:
        """Update an existing memory in SQLite and re-vectorize."""
        memory.updated_at = datetime.now()
        await self._storage.db.execute(
            "UPDATE memories SET content = ?, memory_type = ?, confidence = ?, tags = ?, updated_at = ? WHERE id = ?",
            (
                memory.content,
                memory.memory_type.value,
                memory.confidence,
                ",".join(memory.tags),
                memory.updated_at.isoformat(),
                memory.id,
            ),
        )
        embedding = await self._llm.embed(memory.content)
        await self._storage.vector.upsert("memories", [
            VectorRecord(
                id=memory.id,
                embedding=embedding,
                metadata={"type": memory.memory_type.value},
            )
        ])
        return memory

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory from SQLite and ChromaDB. Returns True if existed."""
        row = await self._storage.db.fetch_one(
            "SELECT id FROM memories WHERE id = ?", (memory_id,)
        )
        if row is None:
            return False
        await self._storage.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        await self._storage.vector.delete("memories", [memory_id])
        return True

    # ── Extraction ────────────────────────────────────────────

    async def extract_from_messages(
        self,
        messages: list[dict],
        source: str = "claude_code",
    ) -> list[Memory]:
        """Extract memories from conversation, dedup, and persist.

        Pipeline:
        1. LLM extracts raw memories from the conversation
        2. For each extracted memory, check vector similarity against existing
        3. Skip if similarity > dedup_threshold (already known)
        4. Save new memories to storage
        """
        raw = await self._llm.extract_memories(messages)
        saved: list[Memory] = []

        for item in raw:
            # Dedup: check if a very similar memory already exists
            embedding = await self._llm.embed(item.content)
            similar = await self._storage.vector.search(
                "memories", embedding, top_k=1
            )
            if similar and similar[0].score >= self._dedup_threshold:
                continue  # Already exists, skip

            memory = Memory(
                content=item.content,
                memory_type=MemoryType(item.memory_type),
                source=source,
                confidence=item.confidence,
            )
            await self.save(memory)
            saved.append(memory)

        return saved

    # ── Recall ────────────────────────────────────────────────

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        memory_type: MemoryType | None = None,
    ) -> list[Memory]:
        """Semantic search: embed query, search ChromaDB, fetch full records."""
        query_embedding = await self._llm.embed(query)
        where = {"type": memory_type.value} if memory_type else None
        results = await self._storage.vector.search(
            "memories", query_embedding, top_k=top_k, where=where
        )

        memories: list[Memory] = []
        for r in results:
            row = await self._storage.db.fetch_one(
                "SELECT * FROM memories WHERE id = ?", (r.id,)
            )
            if row:
                memories.append(self._row_to_memory(row))
        return memories

    # ── Summarization ─────────────────────────────────────────

    async def summarize_conversation(
        self,
        messages: list[dict],
    ) -> ConversationSummary:
        """Generate a conversation summary using the memory_summarize prompt."""
        from memora.llm import PromptTemplate

        conversation = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        tpl = PromptTemplate()
        system, user = tpl.render("memory_summarize", messages=conversation)

        raw = await self._llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], temperature=0.3)

        return self._parse_summary(raw)

    def _parse_summary(self, raw: str) -> ConversationSummary:
        """Parse LLM JSON response into a ConversationSummary."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return ConversationSummary(title="Untitled", summary=raw[:200])

        return ConversationSummary(
            title=data.get("title", "Untitled"),
            summary=data.get("summary", ""),
            key_points=data.get("key_points", []),
        )

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _row_to_memory(row: dict) -> Memory:
        """Convert a SQLite row dict to a Memory model."""
        return Memory(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            source=row.get("source", ""),
            confidence=row.get("confidence", 1.0),
            tags=[t for t in row.get("tags", "").split(",") if t],
            access_count=row.get("access_count", 0),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
