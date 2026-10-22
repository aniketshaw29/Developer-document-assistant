"""Document ingestion pipeline.

Turns raw documents (LlamaIndex `Document` objects) into chunks with
metadata, embeds them, and stores the vectors in ChromaDB. Chunking
strategy is chosen per file type — code uses AST-aware splitting,
markdown splits on headings, and plain text uses sentence-aware splitting.
"""

import hashlib
import re
from typing import Sequence

from llama_index.core import Document
from llama_index.core.node_parser import CodeSplitter, MarkdownNodeParser, SentenceSplitter

from app.core.dependencies import get_chroma_client, get_embed_model

# Languages understood by the tree-sitter based CodeSplitter.
CODE_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".css": "css",
}

# Markdown / plain text documentation extensions.
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".rst", ".txt"}

# Directories that should never be indexed from a cloned repo.
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "dist",
    "build",
    ".next",
    "target",
    "vendor",
}

# Binary / asset files that carry no retrievable text.
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".zip",
    ".gz",
    ".tar",
    ".lock",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pyc",
}


def is_indexable_file(path: str) -> bool:
    """Return True if the given file path should be indexed."""
    import os

    name = os.path.basename(path)
    if name.startswith(".") and name not in (".env.example",):
        return False
    # Machine-generated lock files carry no retrievable knowledge.
    if name in {
        "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml",
        "yarn.lock", "Cargo.lock", "Gemfile.lock", "poetry.lock",
        "Pipfile.lock", "composer.lock", "go.sum",
    }:
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in BINARY_EXTENSIONS:
        return False
    # Files with known extensions.
    if ext in CODE_LANGUAGES or ext in MARKDOWN_EXTENSIONS:
        return True
    # Extensionless common documentation files (README, CHANGELOG, etc.).
    if not ext and name.upper() in {
        "README", "CHANGELOG", "CHANGES", "HISTORY", "LICENSE",
        "LICENSES", "CONTRIBUTING", "AUTHORS", "COPYING",
    }:
        return True
    return False


def make_document_id(collection_name: str, content: str) -> str:
    """Stable chunk id derived from collection + content hash.

    Used with upsert so re-indexing the same content is idempotent.
    """
    digest = hashlib.sha256(f"{collection_name}:{content}".encode()).hexdigest()[:32]
    return digest


def _choose_splitter(ext: str):
    """Return the best node parser for a given file extension."""
    ext = ext.lower()
    if ext in MARKDOWN_EXTENSIONS:
        # MarkdownNodeParser splits on heading boundaries, preserving structure.
        return MarkdownNodeParser()
    if ext in CODE_LANGUAGES:
        # CodeSplitter uses tree-sitter to split at function/class boundaries.
        return CodeSplitter(
            language=CODE_LANGUAGES[ext],
            chunk_lines=40,
            chunk_lines_overlap=15,
            max_chars=1500,
        )
    # Fallback: plain sentence-aware splitting.
    return SentenceSplitter(chunk_size=512, chunk_overlap=50)


def split_document(doc: Document) -> list[Document]:
    """Split a single source document into chunked sub-documents.

    Chunks inherit the source metadata (file path, repo, language, etc.)
    so retrieval can attribute answers to exact sources. An explicit
    `file_type` metadata value (e.g. "markdown") takes priority over the
    file extension — used for converted content like OpenAPI markdown.
    """
    file_type = doc.metadata.get("file_type", "")
    ext = ""
    if file_type == "markdown":
        ext = ".md"
    elif doc.metadata.get("file_path"):
        match = re.search(r"\.[^./\\]+$", doc.metadata["file_path"])
        ext = match.group(0) if match else ""
    parser = _choose_splitter(ext)
    nodes = parser.get_nodes_from_documents([doc])
    # Reuse the source document's metadata on every chunk.
    return [
        Document(text=node.get_content(), metadata=dict(doc.metadata))
        for node in nodes
    ]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured embedding model."""
    embed_model = get_embed_model()
    return [list(embedding) for embedding in embed_model.get_text_embedding_batch(texts)]


def ingest_documents(documents: Sequence[Document], collection_name: str) -> int:
    """Embed and store the given documents in the named collection.

    Returns the number of chunks written. Uses upsert semantics so
    re-ingesting a source replaces (rather than duplicates) its chunks.
    """
    if not documents:
        return 0

    # Build the flat list of chunks with deduped ids.
    chunks: list[Document] = []
    for doc in documents:
        chunks.extend(split_document(doc))

    seen_ids: set[str] = set()
    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []
    for chunk in chunks:
        content = chunk.get_content().strip()
        if not content:
            continue  # Skip empty chunks.
        doc_id = make_document_id(collection_name, content)
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        ids.append(doc_id)
        texts.append(content)
        metadatas.append(chunk.metadata)

    if not ids:
        return 0

    # Embed in batches and upsert into Chroma. ChromaDB accepts ~5461 elements
    # per query, so we batch far below that to keep memory bounded.
    embed_model = get_embed_model()
    batch_size = 64
    collection = get_chroma_client().get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )

    try:
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]
            embeddings = [
                list(embedding)
                for embedding in embed_model.get_text_embedding_batch(batch_texts)
            ]
            collection.upsert(
                ids=batch_ids,
                documents=batch_texts,
                embeddings=embeddings,
                metadatas=batch_metas,
            )
    except ConnectionError as exc:
        # No embedding provider reachable (no OpenAI key, Ollama down).
        raise ConnectionError(
            "No embedding provider available. Set OPENAI_API_KEY in backend/.env "
            "or start Ollama (ollama serve && ollama pull nomic-embed-text)."
        ) from exc

    return len(ids)
