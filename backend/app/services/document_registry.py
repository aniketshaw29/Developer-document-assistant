"""Document metadata registry.

Persists lightweight metadata about each indexed document (title, source
type, chunk count, timestamps) to a JSON file so the UI can list
documents without querying ChromaDB.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

# Lock guards concurrent registry reads/writes.
_lock = threading.Lock()


def _registry_path() -> Path:
    """Registry file lives next to the ChromaDB data dir (computed lazily)."""
    return settings.chroma_persist_path.parent / "documents.json"


def _load() -> dict:
    """Read the registry from disk (empty dict if missing/corrupt)."""
    path = _registry_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    """Write the registry to disk atomically."""
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def register_document(
    doc_id: str,
    title: str,
    source_type: str,
    files_indexed: int,
    chunks_created: int,
    source: str | None = None,
) -> dict:
    """Add or update a document entry and return its metadata dict.

    `source` holds the original URL (GitHub repo / OpenAPI spec) so the
    document can be re-indexed later without user re-entry.
    """
    entry = {
        "id": doc_id,
        "title": title,
        "source_type": source_type,
        "source": source,
        "files_indexed": files_indexed,
        "chunks_created": chunks_created,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        data = _load()
        # Preserve the original created_at if the doc already exists.
        existing = data.get(doc_id)
        if existing and existing.get("created_at"):
            entry["created_at"] = existing["created_at"]
        data[doc_id] = entry
        _save(data)
    return entry


def list_documents() -> list[dict]:
    """Return all registered documents, newest first."""
    data = _load()
    docs = sorted(data.values(), key=lambda d: d.get("created_at", ""), reverse=True)
    return docs


def get_document(doc_id: str) -> dict | None:
    """Return a single document entry, or None."""
    return _load().get(doc_id)


def unregister_document(doc_id: str) -> bool:
    """Remove a document entry. Returns True if it existed."""
    with _lock:
        data = _load()
        removed = data.pop(doc_id, None) is not None
        if removed:
            _save(data)
        return removed
