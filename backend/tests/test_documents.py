"""Tests for the ingestion pipeline and document registry."""

import pytest
from llama_index.core import Document

from app.core.dependencies import list_collections
from app.rag.ingestion import ingest_documents
from app.services.document_registry import (
    list_documents,
    register_document,
    unregister_document,
)


def _sample_doc(text: str, path: str = "docs/guide.md") -> Document:
    """Build a Document with realistic metadata."""
    return Document(text=text, metadata={"file_path": path, "source_type": "test"})


def test_ingest_creates_collection():
    """Ingesting documents creates a ChromaDB collection and returns chunk count."""
    doc = _sample_doc(
        "# Guide\n\nKafka retries are configured with the retries property. "
        "Set it to a positive integer to enable retries."
    )
    count = ingest_documents([doc], "test_ingest")
    assert count > 0
    assert "test_ingest" in list_collections()


def test_ingest_is_idempotent():
    """Re-ingesting identical content does not create duplicate chunks."""
    doc = _sample_doc("Duplicate content that should be upserted once.")
    first = ingest_documents([doc], "test_idem")
    second = ingest_documents([doc], "test_idem")
    assert first == second
    assert first == 1


def test_empty_documents_noop():
    """Ingesting no documents returns zero without creating a collection."""
    assert ingest_documents([], "test_empty") == 0


def test_registry_roundtrip():
    """register / list / unregister round-trips correctly."""
    register_document("doc_1", "Title", "upload", files_indexed=2, chunks_created=5)
    docs = list_documents()
    assert any(d["id"] == "doc_1" and d["chunks_created"] == 5 for d in docs)
    assert unregister_document("doc_1") is True
    assert unregister_document("doc_1") is False


def test_registry_keeps_created_at():
    """Re-registering a doc preserves its original created_at."""
    register_document("doc_2", "T", "upload", files_indexed=1, chunks_created=1)
    first = list_documents()
    created = next(d["created_at"] for d in first if d["id"] == "doc_2")
    register_document("doc_2", "T", "upload", files_indexed=3, chunks_created=4)
    after = list_documents()
    updated = next(d for d in after if d["id"] == "doc_2")
    assert updated["created_at"] == created
    assert updated["chunks_created"] == 4
    unregister_document("doc_2")
