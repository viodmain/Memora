"""API Key authentication middleware."""

from __future__ import annotations

import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key() -> str:
    """Read API key from environment. Empty = auth disabled."""
    return os.environ.get("MEMORA_API_KEY", "")


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Verify API key if configured. Returns key or raises 401.

    If MEMORA_API_KEY is not set, authentication is disabled.
    """
    required_key = get_api_key()
    if not required_key:
        return ""  # Auth disabled

    if not api_key or api_key != required_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return api_key
