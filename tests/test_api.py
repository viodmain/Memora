"""Tests for FastAPI routes."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from memora.api.app import app


@pytest.fixture
def mock_app():
    """Create a mock App for API testing."""
    mock = MagicMock()
    mock.memory.save = AsyncMock(return_value=MagicMock(model_dump=lambda: {"id": "1", "content": "test"}))
    mock.memory.recall = AsyncMock(return_value=[])
    mock.memory.extract_from_messages = AsyncMock(return_value=[])
    mock.memory.list = AsyncMock(return_value=[])
    mock.memory.get = AsyncMock(return_value=None)
    mock.memory.delete = AsyncMock(return_value=False)

    mock.rag.search = AsyncMock(return_value=[])
    mock.rag.ingest = AsyncMock(return_value=MagicMock(model_dump=lambda: {"id": "1", "title": "test"}))
    mock.rag.list_documents = AsyncMock(return_value=[])
    mock.rag.get_document = AsyncMock(return_value=None)
    mock.rag.delete_document = AsyncMock(return_value=False)

    mock.prompt.save = AsyncMock(return_value=MagicMock(model_dump=lambda: {"id": "1", "name": "test"}))
    mock.prompt.list = AsyncMock(return_value=[])
    mock.prompt.get = AsyncMock(return_value=(
        MagicMock(model_dump=lambda: {"name": "test"}),
        MagicMock(model_dump=lambda: {"version": 1, "content": "test"}),
    ))
    mock.prompt.score = AsyncMock()
    mock.prompt.compare = AsyncMock(return_value={"content_changed": True})
    mock.prompt.optimize = AsyncMock(return_value="optimized")
    mock.prompt.delete = AsyncMock(return_value=False)

    mock.search.search = AsyncMock(return_value=[])

    return mock


@pytest.fixture
def client(mock_app):
    """Create test client with mocked App."""
    from memora.api.app import get_app
    app.dependency_overrides = {}

    # Override the get_app dependency
    def override_get_app():
        return mock_app

    # Patch get_app in the route modules
    with patch("memora.api.routes.memory.get_app", return_value=mock_app), \
         patch("memora.api.routes.knowledge.get_app", return_value=mock_app), \
         patch("memora.api.routes.prompt.get_app", return_value=mock_app), \
         patch("memora.api.routes.search.get_app", return_value=mock_app):
        transport = ASGITransport(app=app)
        yield AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_root(client):
    async with client as c:
        resp = await c.get("/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Memora"


@pytest.mark.asyncio
async def test_health(client):
    async with client as c:
        resp = await c.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_memory_save(client, mock_app):
    async with client as c:
        resp = await c.post("/api/memory/save", json={"content": "test", "memory_type": "fact"})
        assert resp.status_code == 200
        mock_app.memory.save.assert_called_once()


@pytest.mark.asyncio
async def test_memory_recall(client, mock_app):
    async with client as c:
        resp = await c.get("/api/memory/recall", params={"query": "test"})
        assert resp.status_code == 200
        mock_app.memory.recall.assert_called_once()


@pytest.mark.asyncio
async def test_memory_list(client, mock_app):
    async with client as c:
        resp = await c.get("/api/memory/")
        assert resp.status_code == 200
        mock_app.memory.list.assert_called_once()


@pytest.mark.asyncio
async def test_search(client, mock_app):
    async with client as c:
        resp = await c.get("/api/search/", params={"query": "test"})
        assert resp.status_code == 200
        mock_app.search.search.assert_called_once()


@pytest.mark.asyncio
async def test_prompt_list(client, mock_app):
    async with client as c:
        resp = await c.get("/api/prompt/")
        assert resp.status_code == 200
        mock_app.prompt.list.assert_called_once()


@pytest.mark.asyncio
async def test_knowledge_search(client, mock_app):
    async with client as c:
        resp = await c.get("/api/knowledge/search", params={"query": "test"})
        assert resp.status_code == 200
        mock_app.rag.search.assert_called_once()
