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
    """Raised when no embedding provider is available."""


class _GatewayEmbedding:
    """Embeddings via an OpenAI-compatible gateway (e.g. a LiteLLM proxy).

    Routes every embedding call through the single configured endpoint using
    LiteLLM's OpenAI-compatible path (``openai/<model>`` + api_base + api_key).
    Implements the subset of the LlamaIndex embedding interface used by the
    ingestion and retrieval pipelines.
    """

    def __init__(self, base_url: str, api_key: str, model: str):
        self._base_url = base_url
        self._api_key = api_key
        self._model = f"openai/{model}"

    def _embed(self, texts: list[str]) -> list[list[float]]:
        import litellm

        response = litellm.embedding(
            model=self._model,
            input=texts,
            api_base=self._base_url,
            api_key=self._api_key,
        )
        return [item["embedding"] for item in response["data"]]

    def get_text_embedding(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def get_query_embedding(self, text: str) -> list[float]:
        return self.get_text_embedding(text)

    def get_text_embedding_batch(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)


def get_embed_model():
    """Return the embedding model, choosing the provider based on settings.

    Priority: gateway (if LLM_BASE_URL is set) → OpenAI → Gemini →
    Ollama (local fallback, requires `ollama pull nomic-embed-text`).
    """
    global _embed_model
    if _embed_model is None:
        if settings.gateway_enabled:
            _embed_model = _GatewayEmbedding(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.embedding_model,
            )
        elif settings.openai_api_key:
            _embed_model = OpenAIEmbedding(
                model=settings.embedding_model, api_key=settings.openai_api_key
            )
        else:
            # Local fallback: requires `ollama pull nomic-embed-text`.
            ollama_embed_model = (
                settings.embedding_model
                if not settings.embedding_model.startswith("text-embedding")
                else "nomic-embed-text"
            )
            _embed_model = OllamaEmbedding(
                model_name=ollama_embed_model,
                base_url=settings.ollama_base_url,
            )
    return _embed_model


def init_llama_settings() -> None:
    """Globally configure LlamaIndex defaults.

    This is called once at app startup so that ingestion and retrieval
    share a single embedding model configuration.
    """
    Settings.embed_model = get_embed_model()
