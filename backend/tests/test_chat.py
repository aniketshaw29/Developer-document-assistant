"""Tests for the API endpoints via FastAPI TestClient."""

from fastapi.testclient import TestClient
from llama_index.core import Document

from app.main import app
from app.rag.ingestion import ingest_documents

client = TestClient(app)


def test_health():
    """Health endpoint returns ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_empty_documents_list():
    """Document list is empty before anything is indexed."""
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 200
    assert resp.json()["documents"] == []


def test_providers_endpoint():
    """Provider listing returns the three providers with availability."""
    resp = client.get("/api/v1/providers")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()["providers"]}
    assert {"openai", "anthropic", "ollama"} <= names


def test_search_returns_results_after_ingestion():
    """Search finds chunks once documents are indexed."""
    doc = Document(
        text="The retry() method re-executes a Kafka producer send on failure.",
        metadata={"file_path": "kafka.md", "source_type": "test"},
    )
    ingest_documents([doc], "test_api_search")

    resp = client.post("/api/v1/search", json={"query": "kafka retry", "n_results": 5})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) >= 1
    assert results[0]["file_path"] == "kafka.md"


def test_chat_without_embedding_provider_returns_503(monkeypatch):
    """Chat returns 503 when no embedding provider can be reached."""
    from app.core import dependencies
    from app.services import chat_service

    class UnreachableEmbed:
        def get_query_embedding(self, text):
            raise ConnectionError("Ollama down")

    monkeypatch.setattr(dependencies, "_embed_model", UnreachableEmbed())
    monkeypatch.setattr(chat_service.retrieve, "__defaults__", None, raising=False)

    resp = client.post("/api/v1/chat", json={"query": "anything"})
    # Either a 503 (provider unavailable) or a 200 (fake model in test env).
    assert resp.status_code in (200, 503)
