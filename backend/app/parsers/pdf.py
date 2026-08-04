"""PDF text extraction using PyMuPDF.

Extracts plain text page by page, preserving page boundaries in the
output so retrieval can point to specific pages.
"""

from pathlib import Path

import fitz  # PyMuPDF


def extract_pdf(file_path: str | Path) -> str:
    """Return the full text content of a PDF, page markers included.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Concatenated text with `--- Page N ---` separators between pages.
    """
    doc = fitz.open(str(file_path))
    try:
        parts: list[str] = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue  # Skip scanned / empty pages.
            parts.append(f"--- Page {page_num} ---\n{text}")
        return "\n\n".join(parts)
    finally:
        doc.close()
