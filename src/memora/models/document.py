"""Document and chunk models for RAG."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
import uuid


class Document(BaseModel):
    """Metadata for an ingested document."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    source_path: str
    source_type: Literal["file", "url", "conversation"]
    file_type: str
    chunk_count: int = 0
    ingested_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A single chunk of a document, with content and metadata."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    document_id: str
    content: str
    chunk_index: int
    metadata: dict = Field(default_factory=dict)
