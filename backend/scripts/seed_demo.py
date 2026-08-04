#!/usr/bin/env python
"""Seed the index with a realistic demo knowledge base.

Populates ChromaDB with an OpenAPI spec and a documentation-heavy GitHub
repo so the chat has something interesting to answer from. Requires an
embedding provider (OpenAI key or local Ollama) and internet access.

Usage (from the `backend/` directory):

    ../venv/bin/python scripts/seed_demo.py
    SEED_REPO=https://github.com/kubernetes/website ../venv/bin/python scripts/seed_demo.py
    SEED_SPEC= SEED_REPO= ...   # empty value skips that source
"""

import os
import sys

# Make the `app` package importable when run from the backend/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import document_service  # noqa: E402


def seed_source(label: str, fn):
    """Run an indexing call, printing a friendly result or error."""
    print(f"\n→ Indexing {label} …")
    try:
        meta = fn()
    except Exception as exc:
        print(f"  ✗ Failed: {exc}")
        return False
    print(
        f"  ✓ {meta['title']}\n"
        f"    {meta['files_indexed']} files, {meta['chunks_created']} chunks, "
        f"id={meta['id']}"
    )
    return True


def main() -> None:
    """Index the configured demo sources (env-overridable)."""
    repo_url = os.environ.get(
        "SEED_REPO", "https://github.com/awsdocs/aws-lambda-developer-guide"
    )
    spec_url = os.environ.get(
        "SEED_SPEC", "https://petstore3.swagger.io/api/v3/openapi.json"
    )

    results = []
    if spec_url:
        results.append(
            seed_source(f"OpenAPI spec {spec_url}", lambda: document_service.index_openapi(spec_url))
        )
    if repo_url:
        results.append(
            seed_source(f"GitHub repo {repo_url}", lambda: document_service.index_github(repo_url))
        )

    print("\n" + ("=" * 50))
    print(f"Seeded {sum(results)}/{len(results)} sources.")
    print("Start the backend, then ask: 'How do I create a Pet?' or 'What does"
          " the API expose?'")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
