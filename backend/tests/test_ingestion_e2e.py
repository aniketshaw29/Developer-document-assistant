"""End-to-end ingestion tests for GitHub and OpenAPI sources.

Network calls (git clone / HTTP fetch) are mocked so tests run offline.
Ingestion/retrieval uses the fake embedding model from conftest.
"""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_fake_clone(files: dict[str, str]):
    """Return a `Repo.clone_from` mock that writes fake files into the target dir."""

    def fake_clone_from(url, target_dir, **kwargs):
        target = Path(target_dir)
        for rel_path, content in files.items():
            file_path = target / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                file_path.write_bytes(content)
            else:
                file_path.write_text(content)

    return fake_clone_from


def test_github_ingestion_endpoint(monkeypatch):
    """POST /documents/github indexes files from a (mocked) cloned repo."""
    from app.parsers import github as github_module

    monkeypatch.setattr(
        github_module.Repo,
        "clone_from",
        _make_fake_clone(
            {
                "README.md": "# My Library\n\nA great library for handling Kafka retries.",
                "src/kafka.py": (
                    "def configure_retry(broker, retries):\n"
                    "    \"\"\"Configure Kafka retry.\"\"\"\n"
                    "    return {'bootstrap.servers': broker, 'retries': retries}\n"
                ),
                "package-lock.json": '{"ignored": true}',  # Should be skipped.
                "logo.png": b"\x89PNG\r\n\x1a\n",  # Binary, should be skipped.
            }
        ),
    )

    resp = client.post(
        "/api/v1/documents/github",
        json={"repo_url": "https://github.com/octocat/Hello-World"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source_type"] == "github"
    assert data["files_indexed"] == 2  # README.md + kafka.py, not lock/png
    assert data["chunks_created"] >= 2

    # Confirm retrieval finds the Kafka code.
    search = client.post(
        "/api/v1/search", json={"query": "configure kafka retry", "n_results": 5}
    )
    assert search.status_code == 200
    file_paths = {r["file_path"] for r in search.json()["results"]}
    assert "src/kafka.py" in file_paths or "README.md" in file_paths

    # Cleanup so we don't pollute other tests.
    client.delete(f"/api/v1/documents/{data['id']}")


def test_github_ingestion_invalid_url():
    """POST /documents/github rejects malformed URLs with 400."""
    resp = client.post(
        "/api/v1/documents/github",
        json={"repo_url": "https://gitlab.com/owner/repo"},
    )
    assert resp.status_code == 400
    assert "Invalid GitHub URL" in resp.json()["detail"]


def test_reindex_document(monkeypatch):
    """POST /documents/{id}/reindex re-clones the stored source URL."""
    from app.parsers import github as github_module

    call_count = {"n": 0}

    def counting_clone(url, target_dir, **kwargs):
        call_count["n"] += 1
        target = Path(target_dir)
        (target / "README.md").write_text(
            "# Library\n\nUpdated docs on Kafka retries.", encoding="utf-8"
        )

    monkeypatch.setattr(github_module.Repo, "clone_from", counting_clone)

    # Initial index.
    resp = client.post(
        "/api/v1/documents/github",
        json={"repo_url": "https://github.com/octocat/Hello-World"},
    )
    assert resp.status_code == 200, resp.text
    doc_id = resp.json()["id"]
    assert call_count["n"] == 1

    # Re-index uses the stored source, no URL in the request body.
    reindex = client.post(f"/api/v1/documents/{doc_id}/reindex")
    assert reindex.status_code == 200, reindex.text
    assert call_count["n"] == 2

    # Uploaded docs can't be re-indexed — expect 404 semantics.
    missing = client.post("/api/v1/documents/nonexistent/reindex")
    assert missing.status_code == 404

    client.delete(f"/api/v1/documents/{doc_id}")


def test_github_ingestion_branch_not_found(monkeypatch):
    """A git error surfaces as a readable 422 response."""
    from git import exc as git_exc
    from app.parsers import github as github_module

    def failing_clone(url, target_dir, **kwargs):
        raise git_exc.GitCommandError("clone", 128, stderr=b"couldn't find remote ref old")

    monkeypatch.setattr(github_module.Repo, "clone_from", failing_clone)

    resp = client.post(
        "/api/v1/documents/github",
        json={"repo_url": "https://github.com/octocat/Hello-World", "branch": "old"},
    )
    assert resp.status_code == 422
    assert "Branch" in resp.json()["detail"]


def test_openapi_ingestion_endpoint(monkeypatch):
    """POST /documents/openapi fetches a spec and indexes its endpoints."""
    from app.parsers import openapi as openapi_module

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Orders API", "version": "2.0"},
        "paths": {
            "/orders": {
                "get": {"summary": "List orders", "responses": {"200": {"description": "OK"}}},
                "post": {
                    "summary": "Create order",
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Order"}}
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
        "components": {
            "schemas": {
                "Order": {
                    "type": "object",
                    "properties": {"id": {"type": "integer", "description": "Order ID"}},
                }
            }
        },
    }
    monkeypatch.setattr(openapi_module, "_fetch_spec", lambda url: spec)

    resp = client.post(
        "/api/v1/documents/openapi",
        json={"spec_url": "https://api.example.com/orders/swagger.json"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source_type"] == "openapi"
    assert data["title"] == "Orders API"
    assert data["chunks_created"] >= 1

    # Retrieval should surface the endpoint documentation.
    search = client.post(
        "/api/v1/search", json={"query": "which endpoint creates orders", "n_results": 5}
    )
    assert search.status_code == 200
    assert search.json()["results"], "no results for openapi spec"

    client.delete(f"/api/v1/documents/{data['id']}")


def test_openapi_ingestion_404(monkeypatch):
    """A 404 from the spec URL surfaces as a readable 422."""
    from app.parsers import openapi as openapi_module

    def failing_fetch(url):
        raise RuntimeError(f"Spec not found at: {url}. Check the URL and try again.")

    monkeypatch.setattr(openapi_module, "_fetch_spec", failing_fetch)

    resp = client.post(
        "/api/v1/documents/openapi",
        json={"spec_url": "https://example.com/missing.json"},
    )
    assert resp.status_code == 422
    assert "Spec not found" in resp.json()["detail"]


def test_openapi_ingestion_invalid_url():
    """POST /documents/openapi rejects non-HTTP URLs with 400."""
    resp = client.post(
        "/api/v1/documents/openapi",
        json={"spec_url": "ftp://example.com/spec.json"},
    )
    assert resp.status_code == 400
    assert "Invalid URL scheme" in resp.json()["detail"]
