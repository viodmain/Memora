"""Prompt and version models."""

from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class Prompt(BaseModel):
    """A prompt template with version tracking."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    latest_version: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class PromptVersion(BaseModel):
    """A specific version of a prompt."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    prompt_id: str
    version: int
    content: str
    variables: list[str] = Field(default_factory=list)
    score: float | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
