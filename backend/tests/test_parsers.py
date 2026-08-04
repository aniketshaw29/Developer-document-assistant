"""Tests for the document parsers."""

from pathlib import Path

from app.parsers.code import parse_code_file
from app.parsers.github import _validate_github_url
from app.parsers.markdown import parse_markdown_file
from app.parsers.openapi import openapi_to_markdown, _validate_url
from app.parsers.pdf import extract_pdf
from app.rag.ingestion import is_indexable_file


def test_markdown_parser(tmp_path: Path):
    """Markdown files parse into documents with file metadata."""
    md = tmp_path / "guide.md"
    md.write_text("# Title\n\nBody text here.\n")
    doc = parse_markdown_file(md)
    assert doc is not None
    assert doc.metadata["file_path"] == str(md)
    assert doc.metadata["file_type"] == "markdown"
    assert "Title" in doc.text


def test_code_parser(tmp_path: Path):
    """Code files parse with language metadata."""
    py = tmp_path / "app.py"
    py.write_text("def hello():\n    return 'world'\n")
    doc = parse_code_file(py)
    assert doc is not None
    assert doc.metadata["language"] == "python"


def test_code_parser_rejects_unknown(tmp_path: Path):
    """Unknown extensions return None."""
    unknown = tmp_path / "file.xyz"
    unknown.write_text("not code")
    assert parse_code_file(unknown) is None


def test_pdf_extraction(tmp_path: Path):
    """PDF text extraction returns page-marked content."""
    import fitz

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Kafka retry configuration")
    doc.save(str(pdf_path))
    doc.close()

    text = extract_pdf(pdf_path)
    assert "Kafka retry configuration" in text
    assert "Page 1" in text


def test_openapi_to_markdown():
    """OpenAPI specs convert into endpoint documentation markdown."""
    spec = {
        "info": {"title": "Order API", "version": "1.0"},
        "paths": {
            "/orders": {
                "post": {
                    "summary": "Create an order",
                    "parameters": [
                        {"name": "X-API-Key", "in": "header", "required": True, "type": "string"}
                    ],
                    "responses": {
                        "201": {"description": "Created", "content": {"application/json": {}}}
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "Order": {
                    "properties": {"id": {"type": "integer", "description": "Order id"}}
                }
            }
        },
    }
    md = openapi_to_markdown(spec)
    assert "POST `/orders`" in md
    assert "Create an order" in md
    assert "Order" in md


def test_is_indexable_file():
    """Indexability filters by extension."""
    assert is_indexable_file("README.md")
    assert is_indexable_file("main.py")
    assert not is_indexable_file("image.png")
    assert not is_indexable_file(".hidden.py")


def test_validate_github_url():
    """GitHub URL validation accepts valid URLs and rejects invalid ones."""
    assert _validate_github_url("https://github.com/kubernetes/kubernetes.git") == \
        "https://github.com/kubernetes/kubernetes"
    assert _validate_github_url("https://github.com/octocat/Hello-World") == \
        "https://github.com/octocat/Hello-World"
    assert _validate_github_url("not-a-url") is None
    assert _validate_github_url("https://gitlab.com/owner/repo") is None
    assert _validate_github_url("https://github.com/owner") is None


def test_validate_openapi_url():
    """OpenAPI URL validation accepts HTTP(S) and rejects others."""
    assert _validate_url("https://petstore3.swagger.io/api/v3/openapi.json") == \
        "https://petstore3.swagger.io/api/v3/openapi.json"
    assert _validate_url("http://localhost:8080/spec.json") == \
        "http://localhost:8080/spec.json"
    try:
        _validate_url("ftp://example.com/spec.json")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    try:
        _validate_url("not-a-url")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
