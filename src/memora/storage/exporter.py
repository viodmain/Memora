"""Data export — JSON and CSV formats."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from memora.storage.database import SQLiteStore


async def export_memories_json(db: SQLiteStore, path: str) -> int:
    """Export all memories to a JSON file.

    Returns the number of exported records.
    """
    rows = await db.fetch_all("SELECT * FROM memories ORDER BY created_at")
    records = []
    for r in rows:
        records.append({
            "id": r["id"],
            "content": r["content"],
            "memory_type": r["memory_type"],
            "source": r["source"],
            "confidence": r["confidence"],
            "tags": r["tags"],
            "access_count": r["access_count"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return len(records)


async def export_memories_csv(db: SQLiteStore, path: str) -> int:
    """Export all memories to a CSV file.

    Returns the number of exported records.
    """
    rows = await db.fetch_all("SELECT * FROM memories ORDER BY created_at")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "content", "memory_type", "source", "confidence", "tags", "access_count", "created_at", "updated_at"])
        for r in rows:
            writer.writerow([
                r["id"], r["content"], r["memory_type"], r["source"],
                r["confidence"], r["tags"], r["access_count"],
                r["created_at"], r["updated_at"],
            ])

    return len(rows)


async def export_documents_json(db: SQLiteStore, path: str) -> int:
    """Export all document metadata to a JSON file."""
    rows = await db.fetch_all("SELECT * FROM documents ORDER BY ingested_at")
    records = []
    for r in rows:
        records.append({
            "id": r["id"],
            "title": r["title"],
            "source_path": r["source_path"],
            "source_type": r["source_type"],
            "file_type": r["file_type"],
            "chunk_count": r["chunk_count"],
            "ingested_at": r["ingested_at"],
        })

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return len(records)


async def export_all_json(db: SQLiteStore, path: str) -> dict[str, int]:
    """Export all data to a single JSON file.

    Returns counts per category.
    """
    memories = await db.fetch_all("SELECT * FROM memories ORDER BY created_at")
    documents = await db.fetch_all("SELECT * FROM documents ORDER BY ingested_at")
    prompts = await db.fetch_all("SELECT * FROM prompts ORDER BY created_at")
    prompt_versions = await db.fetch_all("SELECT * FROM prompt_versions ORDER BY prompt_id, version")

    data = {
        "exported_at": datetime.now().isoformat(),
        "memories": [dict(r) for r in memories],
        "documents": [dict(r) for r in documents],
        "prompts": [dict(r) for r in prompts],
        "prompt_versions": [dict(r) for r in prompt_versions],
    }

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "memories": len(memories),
        "documents": len(documents),
        "prompts": len(prompts),
        "prompt_versions": len(prompt_versions),
    }
