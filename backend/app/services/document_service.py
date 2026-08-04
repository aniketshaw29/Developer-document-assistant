"""Document service — orchestrates the full ingestion lifecycle.

Wraps the parsers + ingestion pipeline behind simple, source-specific
operations used by the API routes: index (github / upload / openapi),
list and delete.
"""

import re
from pathlib import Path

from fastapi import UploadFile

from app.core.dependencies import delete_collection
from app.parsers.github import clone_and_parse_repo, collection_name_for_repo
from app.parsers.markdown import parse_markdown_file
from app.parsers.openapi import parse_openapi_url
from app.parsers.pdf import extract_pdf
from app.rag.ingestion import ingest_documents
from app.services.document_registry import (
    get_document,
    list_documents as registry_list,
    register_document,
    unregister_document,
)


def _safe_collection_name(name: str) -> str:
    """Sanitise a string into a valid ChromaDB collection name."""
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return cleaned[:63]


def index_github(repo_url: str, branch: str | None = None) -> dict:
    """Clone and index a GitHub repository. Returns the document metadata."""
    documents, stats = clone_and_parse_repo(repo_url, branch=branch)
    collection = collection_name_for_repo(repo_url)
    chunks = ingest_documents(documents, collection)
    return register_document(
        doc_id=collection,
        title=repo_url,
        source_type="github",
        source=repo_url,
        files_indexed=stats["files"],
        chunks_created=chunks,
    )


def index_upload(files: list[UploadFile]) -> dict:
    """Index uploaded files (markdown, code, PDF, text). Returns doc metadata."""
    documents = []
    filenames: list[str] = []
    for upload in files:
        filename = upload.filename or "unnamed"
        # Guard against path traversal in the client-provided filename.
        safe_name = Path(filename).name
        filenames.append(safe_name)
        content = upload.file.read()
        ext = Path(safe_name).suffix.lower()
        if ext == ".pdf":
            # Write the PDF to a temp file for PyMuPDF, then parse it.
            tmp = Path("/tmp") / safe_name
            tmp.write_bytes(content)
            try:
                text = extract_pdf(tmp)
                if text.strip():
                    documents.append(
                        _make_document(
                            text, {"file_path": safe_name, "source_type": "upload"}
                        )
                    )
            finally:
                tmp.unlink(missing_ok=True)
        elif ext in {".md", ".markdown", ".rst", ".txt"}:
            text = content.decode("utf-8", errors="ignore")
            if text.strip():
                documents.append(
                    _make_document(
                        text, {"file_path": safe_name, "source_type": "upload"}
                    )
                )
        elif re.search(r"\.[A-Za-z0-9]+$", ext) and content:
            # Treat any other extension as a code/text file.
            text = content.decode("utf-8", errors="ignore")
            if text.strip():
                documents.append(
                    _make_document(
                        text, {"file_path": safe_name, "source_type": "upload"}
                    )
                )

    # Group all uploaded files into one collection derived from the file names.
    title = ", ".join(filenames) or "uploaded files"
    collection = _safe_collection_name(f"upload_{title}"[:60])
    chunks = ingest_documents(documents, collection)
    return register_document(
        doc_id=collection,
        title=title,
        source_type="upload",
        files_indexed=len(filenames),
        chunks_created=chunks,
    )


def index_openapi(spec_url: str) -> dict:
    """Fetch, convert and index an OpenAPI spec. Returns doc metadata."""
    document, stats = parse_openapi_url(spec_url)
    collection = _safe_collection_name(f"openapi_{stats['title']}")
    chunks = ingest_documents([document], collection)
    return register_document(
        doc_id=collection,
        title=stats["title"],
        source_type="openapi",
        source=spec_url,
        files_indexed=1,
        chunks_created=chunks,
    )


def reindex_document(doc_id: str) -> dict | None:
    """Re-index an existing document from its stored source URL.

    Uploaded documents carry no persistent source, so they return None
    (the caller should return a 409 conflict). Raises the same errors as
    the initial index for invalid/unavailable sources.
    """
    entry = get_document(doc_id)
    if not entry:
        return None
    if entry["source_type"] == "github":
        return index_github(entry.get("source", ""))
    if entry["source_type"] == "openapi":
        return index_openapi(entry.get("source", ""))
    return None


def _make_document(text: str, metadata: dict):
    """Build a LlamaIndex Document from raw text + metadata."""
    from llama_index.core import Document as LIDocument

    return LIDocument(text=text, metadata=metadata)


def list_documents() -> list[dict]:
    """Return metadata for all indexed documents."""
    return registry_list()


def delete_document(doc_id: str) -> bool:
    """Delete a document: removes its ChromaDB collection and registry entry."""
    existed = unregister_document(doc_id)
    delete_collection(doc_id)
    return existed
