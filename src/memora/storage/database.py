"""SQLite async storage implementation."""

from typing import Any, Sequence
from pathlib import Path

import aiosqlite

from .migrations import run_migrations


class SQLiteStore:
    """Async SQLite storage for structured data (memories, prompts, documents)."""

    def __init__(self, db_path: str = "data/memora.db") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open connection and run schema migrations."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(self._db)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        """Get the active connection; raises if not initialized."""
        if self._db is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._db

    async def execute(self, sql: str, params: tuple = ()) -> None:
        """Execute a write query (INSERT/UPDATE/DELETE)."""
        await self.db.execute(sql, params)
        await self.db.commit()

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        """Fetch a single row as a dict, or None if not found."""
        cursor = await self.db.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetch_all(self, sql: str, params: tuple = ()) -> Sequence[dict[str, Any]]:
        """Fetch all matching rows as a list of dicts."""
        cursor = await self.db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """Execute a write query for multiple parameter sets."""
        await self.db.executemany(sql, params_list)
        await self.db.commit()
