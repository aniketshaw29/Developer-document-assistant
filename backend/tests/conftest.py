"""Shared pytest fixtures.

The test suite does not call any real LLM provider. A deterministic fake
embedding model is injected so ingestion/retrieval can run offline.
"""

import hashlib

import pytest

from app.core import dependencies


class FakeEmbedModel:
    """Deterministic, provider-free embedding model for tests.

    Produces a 16-dim vector derived from the text hash. Same text always
    yields the same embedding, so retrieval similarity behaves sensibly.
    """

    def get_text_embedding(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).hexdigest()
        return [int(digest[i : i + 2], 16) / 255.0 for i in range(0, 32, 2)]

    def get_query_embedding(self, text: str) -> list[float]:
        return self.get_text_embedding(text)

    def get_text_embedding_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.get_text_embedding(t) for t in texts]


@pytest.fixture(autouse=True)
def fake_embed_model(monkeypatch):
    """Replace the global embedding model with the fake across all tests."""
    monkeypatch.setattr(dependencies, "_embed_model", FakeEmbedModel())
    yield FakeEmbedModel()


@pytest.fixture(autouse=True)
def temp_chroma_dir(monkeypatch, tmp_path):
    """Isolate ChromaDB state per test in a temporary directory.

    Recreates the process-wide Chroma client so it points at the temp dir,
    preventing tests from polluting the real data/ directory or each other.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "chroma_persist_dir", str(tmp_path / "chroma"))
    monkeypatch.setattr(dependencies, "_chroma_client", None)
    yield tmp_path
    monkeypatch.setattr(dependencies, "_chroma_client", None)
