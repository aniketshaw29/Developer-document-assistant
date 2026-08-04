"""FastAPI dependency helpers.

Provide lazily-initialised, shared instances of ChromaDB, embedding models
and LlamaIndex settings to route handlers via FastAPI's dependency system.
"""

import chromadb
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.config import settings

_chroma_client: chromadb.ClientAPI | None = None
_embed_model = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Return the process-wide ChromaDB persistent client.

    Lazily created on first call so the store only opens when needed.
    Uses a persistent client writing to `settings.chroma_persist_path`.
    """
    global _chroma_client
    if _chroma_client is None:
        # Ensure the persistence directory exists before Chroma tries to write.
        settings.chroma_persist_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(settings.chroma_persist_path))
    return _chroma_client


def get_collection(name: str) -> ChromaVectorStore:
    """Get (or create) a ChromaDB collection wrapped in a LlamaIndex vector store.

    Cosine distance is used because our embeddings are normalised.
    """
    client = get_chroma_client()
    # Passing metadata={"hnsw:space": "cosine"} pins the metric at creation time.
    collection = client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"}
    )
    return ChromaVectorStore(chroma_collection=collection)


def delete_collection(name: str) -> None:
    """Remove a ChromaDB collection entirely (used when deleting a document)."""
    client = get_chroma_client()
    try:
        client.delete_collection(name)
    except ValueError:
        # Chroma raises if the collection does not exist — ignore that case.
        pass


def list_collections() -> list[str]:
    """Return the names of every ChromaDB collection (i.e. indexed documents)."""
    client = get_chroma_client()
    return [c.name for c in client.list_collections()]


class NoEmbeddingProviderError(RuntimeError):
    """Raised when neither OpenAI nor Ollama embeddings are available."""


def get_embed_model():
    """Return the embedding model, choosing the provider based on settings.

    OpenAI embeddings are used by default. If no OpenAI key is configured
    we fall back to a local Ollama embedding model so the app still works
    fully offline (e.g. with `ollama pull nomic-embed-text`). If neither
    is available, raise a clear, user-facing error.
    """
    global _embed_model
    if _embed_model is None:
        if settings.openai_api_key:
            _embed_model = OpenAIEmbedding(
                model=settings.embedding_model, api_key=settings.openai_api_key
            )
        else:
            # Offline fallback: requires `ollama pull nomic-embed-text`.
            _embed_model = OllamaEmbedding(
                model_name=settings.embedding_model,
                base_url=settings.ollama_base_url,
            )
    return _embed_model


def init_llama_settings() -> None:
    """Globally configure LlamaIndex defaults.

    This is called once at app startup so that ingestion and retrieval
    share a single embedding model configuration.
    """
    Settings.embed_model = get_embed_model()
