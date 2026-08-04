"""Markdown / text file parsing.

Reads markdown, RST and plain-text files into LlamaIndex documents.
Markdown structure (headings) is preserved for structural chunking.
"""

from pathlib import Path

from llama_index.core import Document

from app.parsers.code import read_text_file


def parse_markdown_file(path: str | Path) -> Document | None:
    """Read a markdown / text file into a LlamaIndex Document.

    Returns None if the file cannot be read or is empty.
    """
    file_path = Path(path)
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
            "file_type": "markdown",
        },
    )
