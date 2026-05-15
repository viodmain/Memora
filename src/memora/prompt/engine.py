"""Prompt engine — implementation."""

from __future__ import annotations

import json
from datetime import datetime

from memora.models.prompt import Prompt, PromptVersion
from memora.storage import Storage
from memora.llm import LLMClient


class PromptEngineImpl:
    """Concrete implementation of the PromptEngine Protocol."""

    def __init__(self, storage: Storage, llm: LLMClient) -> None:
        self._storage = storage
        self._llm = llm

    async def save(
        self,
        name: str,
        content: str,
        description: str = "",
        variables: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Prompt:
        """Save a prompt. Creates new version if name exists, otherwise creates new prompt."""
        now = datetime.now().isoformat()
        variables = variables or []
        tags = tags or []

        # Check if prompt exists
        existing = await self._storage.db.fetch_one(
            "SELECT * FROM prompts WHERE name = ?", (name,)
        )

        if existing:
            # Increment version
            new_version = existing["latest_version"] + 1
            await self._storage.db.execute(
                "UPDATE prompts SET latest_version = ?, description = ?, tags = ? WHERE id = ?",
                (new_version, description, ",".join(tags), existing["id"]),
            )
            prompt_id = existing["id"]
        else:
            # Create new prompt
            import uuid
            prompt_id = uuid.uuid4().hex
            new_version = 1
            await self._storage.db.execute(
                "INSERT INTO prompts (id, name, description, tags, latest_version, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (prompt_id, name, description, ",".join(tags), new_version, now),
            )

        # Create version record
        import uuid
        version_id = uuid.uuid4().hex
        await self._storage.db.execute(
            "INSERT INTO prompt_versions (id, prompt_id, version, content, variables, score, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (version_id, prompt_id, new_version, content, json.dumps(variables), None, "", now),
        )

        return Prompt(
            id=prompt_id,
            name=name,
            description=description,
            tags=tags,
            latest_version=new_version,
            created_at=datetime.fromisoformat(now),
        )

    async def get(self, name: str, version: int | None = None) -> tuple[Prompt, PromptVersion]:
        """Get prompt metadata + specified version (default: latest)."""
        row = await self._storage.db.fetch_one(
            "SELECT * FROM prompts WHERE name = ?", (name,)
        )
        if row is None:
            raise ValueError(f"Prompt not found: {name}")

        prompt = self._row_to_prompt(row)
        target_version = version or prompt.latest_version

        ver_row = await self._storage.db.fetch_one(
            "SELECT * FROM prompt_versions WHERE prompt_id = ? AND version = ?",
            (prompt.id, target_version),
        )
        if ver_row is None:
            raise ValueError(f"Version {target_version} not found for prompt: {name}")

        return prompt, self._row_to_version(ver_row)

    async def list(self, tag: str | None = None) -> list[Prompt]:
        """List prompts, optionally filtered by tag."""
        if tag:
            rows = await self._storage.db.fetch_all(
                "SELECT * FROM prompts WHERE tags LIKE ? ORDER BY created_at DESC",
                (f"%{tag}%",),
            )
        else:
            rows = await self._storage.db.fetch_all(
                "SELECT * FROM prompts ORDER BY created_at DESC"
            )
        return [self._row_to_prompt(r) for r in rows]

    async def score(self, name: str, version: int, score: float) -> None:
        """Rate a prompt version (1-5)."""
        if not 1.0 <= score <= 5.0:
            raise ValueError("Score must be between 1 and 5")

        prompt, _ = await self.get(name, version)
        await self._storage.db.execute(
            "UPDATE prompt_versions SET score = ? WHERE prompt_id = ? AND version = ?",
            (score, prompt.id, version),
        )

    async def compare(self, name: str, v1: int, v2: int) -> dict:
        """Compare two versions of a prompt."""
        _, ver1 = await self.get(name, v1)
        _, ver2 = await self.get(name, v2)

        return {
            "name": name,
            "v1": {"version": ver1.version, "content": ver1.content, "score": ver1.score},
            "v2": {"version": ver2.version, "content": ver2.content, "score": ver2.score},
            "content_changed": ver1.content != ver2.content,
            "score_diff": (ver2.score or 0) - (ver1.score or 0),
        }

    async def optimize(self, name: str, feedback: str = "") -> str:
        """Generate optimization suggestions via LLM."""
        _, ver = await self.get(name)

        from memora.llm import PromptTemplate
        tpl = PromptTemplate()
        system, user = tpl.render(
            "prompt_optimize",
            current_prompt=ver.content,
            feedback=feedback or "No specific feedback",
        )

        raw = await self._llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], temperature=0.7)

        return raw

    async def delete(self, name: str) -> bool:
        """Delete a prompt and all its versions."""
        row = await self._storage.db.fetch_one(
            "SELECT id FROM prompts WHERE name = ?", (name,)
        )
        if row is None:
            return False

        # Delete versions first (cascade should handle this, but be explicit)
        await self._storage.db.execute(
            "DELETE FROM prompt_versions WHERE prompt_id = ?", (row["id"],)
        )
        await self._storage.db.execute(
            "DELETE FROM prompts WHERE id = ?", (row["id"],)
        )
        return True

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _row_to_prompt(row: dict) -> Prompt:
        return Prompt(
            id=row["id"],
            name=row["name"],
            description=row.get("description", ""),
            tags=[t for t in row.get("tags", "").split(",") if t],
            latest_version=row["latest_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_version(row: dict) -> PromptVersion:
        variables = json.loads(row.get("variables", "[]"))
        return PromptVersion(
            id=row["id"],
            prompt_id=row["prompt_id"],
            version=row["version"],
            content=row["content"],
            variables=variables,
            score=row.get("score"),
            notes=row.get("notes", ""),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
