"""Application container — dependency injection and factory."""

from __future__ import annotations

from dataclasses import dataclass

from memora.config import load_config, AppConfig
from memora.storage import Storage, create_storage
from memora.llm import LLMClient, create_llm_client
from memora.memory import MemoryEngine
from memora.memory.engine import MemoryEngineImpl
from memora.rag import RAGEngine
from memora.rag.engine import RAGEngineImpl
from memora.prompt import PromptEngine
from memora.prompt.engine import PromptEngineImpl
from memora.search import SearchService
from memora.search.service import SearchServiceImpl


@dataclass
class App:
    """Application container holding all engine instances.

    Entry points (CLI, API, MCP) access capabilities through this object.
    """
    config: AppConfig
    storage: Storage
    llm: LLMClient
    memory: MemoryEngine
    rag: RAGEngine
    prompt: PromptEngine
    search: SearchService

    async def shutdown(self) -> None:
        """Close all connections."""
        await self.storage.close()


async def create_app(config_path: str = "config/settings.yaml") -> App:
    """Factory: assemble the entire application.

    Dependency injection order:
    1. Load config
    2. Create LLM client (chat + embedding)
    3. Create storage (SQLite + ChromaDB)
    4. Create engines (inject storage + llm)
    5. Create search service (inject engines)
    """
    config = load_config(config_path)

    llm = create_llm_client(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        model=config.llm.model,
        embedding_model=config.embedding.model,
        embedding_base_url=config.embedding.base_url,
        embedding_api_key=config.embedding.api_key,
    )

    storage = await create_storage(config.storage.db_path, config.storage.chroma_path)

    memory_engine = MemoryEngineImpl(storage, llm, config.memory_extraction.dedup_threshold)
    rag_engine = RAGEngineImpl(storage, llm, config.rag.chunk_size, config.rag.chunk_overlap)
    prompt_engine = PromptEngineImpl(storage, llm)
    search_service = SearchServiceImpl(memory_engine, rag_engine, prompt_engine)

    return App(
        config=config,
        storage=storage,
        llm=llm,
        memory=memory_engine,
        rag=rag_engine,
        prompt=prompt_engine,
        search=search_service,
    )
