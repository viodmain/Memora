"""Database schema definitions and migration runner."""

import aiosqlite

SCHEMA_VERSION = 1

TABLES = """
-- memories: extracted conversation memories
CREATE TABLE IF NOT EXISTS memories (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    memory_type TEXT NOT NULL CHECK(memory_type IN ('fact','preference','decision','experience','relationship')),
    source      TEXT DEFAULT '',
    confidence  REAL DEFAULT 1.0,
    tags        TEXT DEFAULT '',
    access_count INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

-- conversations: conversation summaries
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    summary     TEXT NOT NULL,
    key_points  TEXT DEFAULT '[]',
    memory_ids  TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);

-- documents: ingested document metadata
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('file','url','conversation')),
    file_type   TEXT NOT NULL,
    chunk_count INTEGER DEFAULT 0,
    ingested_at TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}'
);

-- document_chunks: chunk metadata (vectors stored in ChromaDB)
CREATE TABLE IF NOT EXISTS document_chunks (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    metadata    TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);

-- prompts: prompt template metadata
CREATE TABLE IF NOT EXISTS prompts (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    description    TEXT DEFAULT '',
    tags           TEXT DEFAULT '',
    latest_version INTEGER DEFAULT 0,
    created_at     TEXT NOT NULL
);

-- prompt_versions: version history for prompts
CREATE TABLE IF NOT EXISTS prompt_versions (
    id         TEXT PRIMARY KEY,
    prompt_id  TEXT NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    version    INTEGER NOT NULL,
    content    TEXT NOT NULL,
    variables  TEXT DEFAULT '[]',
    score      REAL,
    notes      TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(prompt_id, version)
);
CREATE INDEX IF NOT EXISTS idx_pv_prompt ON prompt_versions(prompt_id);

-- tags: tag definitions
CREATE TABLE IF NOT EXISTS tags (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- memory_tags: memory-tag associations
CREATE TABLE IF NOT EXISTS memory_tags (
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    tag_id    TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (memory_id, tag_id)
);

-- search_history: search query log
CREATE TABLE IF NOT EXISTS search_history (
    id           TEXT PRIMARY KEY,
    query        TEXT NOT NULL,
    scope        TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    created_at   TEXT NOT NULL
);

-- schema_version: track migration state
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""


async def run_migrations(db: aiosqlite.Connection) -> None:
    """Execute all pending database migrations.

    Creates tables if they don't exist and tracks schema version.
    """
    await db.executescript(TABLES)

    # Record schema version
    cursor = await db.execute("SELECT version FROM schema_version")
    row = await cursor.fetchone()
    if row is None:
        await db.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    elif row[0] < SCHEMA_VERSION:
        await db.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))

    await db.commit()
