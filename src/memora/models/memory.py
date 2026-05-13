"""Memory and conversation models."""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class MemoryType(str, Enum):
    """Types of memories that can be extracted from conversations."""
    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    EXPERIENCE = "experience"
    RELATIONSHIP = "relationship"


class Memory(BaseModel):
    """A single memory entry extracted from conversation or added manually."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    content: str
    memory_type: MemoryType
    source: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    access_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationSummary(BaseModel):
    """Summary of a conversation with extracted memory references."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
