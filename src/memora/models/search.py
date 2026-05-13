"""Search result model for unified search."""

from typing import Literal, Any
from pydantic import BaseModel


class SearchResult(BaseModel):
    """A unified search result from memory, document, or prompt."""
    content: str
    source_type: Literal["memory", "document", "prompt"]
    source_id: str
    relevance_score: float
    highlight: str = ""
    metadata: dict[str, Any] = {}
