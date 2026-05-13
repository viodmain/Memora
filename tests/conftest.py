"""Shared test fixtures."""

import asyncio
import shutil
import pytest
import pytest_asyncio

from memora.storage import create_storage, Storage
from memora.config import load_config, AppConfig


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def storage(tmp_path) -> Storage:
    """Create a temporary Storage instance for testing."""
    db_path = str(tmp_path / "test.db")
    chroma_path = str(tmp_path / "chroma")
    s = await create_storage(db_path, chroma_path)
    yield s
    await s.close()


@pytest.fixture
def config() -> AppConfig:
    """Load the default config (without env vars)."""
    return AppConfig()
