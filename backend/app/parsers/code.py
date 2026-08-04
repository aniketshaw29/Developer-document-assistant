"""Code file parsing.

Reads source files into LlamaIndex documents. Actual AST-aware chunking
happens later in the ingestion pipeline (via CodeSplitter); this module
handles file discovery and reading with encoding fallbacks.
"""

from pathlib import Path

from llama_index.core import Document

from app.rag.ingestion import CODE_LANGUAGES

# Encodings tried in order when reading a file (most common first).
_ENCODINGS = ("utf-8", "latin-1", "utf-16")


def read_text_file(path: Path) -> str:
    """Read a text file, trying several encodings until one succeeds."""
    for encoding in _ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    # Last resort: read bytes and ignore invalid characters.
    return path.read_bytes().decode("utf-8", errors="ignore")


def parse_code_file(path: str | Path) -> Document | None:
    """Read a single code file into a LlamaIndex Document.

    Returns None for files we don't recognise or that fail to read.
    """
    file_path = Path(path)
    ext = file_path.suffix.lower()
    if ext not in CODE_LANGUAGES:
        return None
    try:
        content = read_text_file(file_path)
    except OSError:
        return None
    if not content.strip():
        return None

    return Document(
        text=content,
        metadata={
            "file_path": str(file_path),
            "language": CODE_LANGUAGES[ext],
            "file_type": "code",
        },
    )
