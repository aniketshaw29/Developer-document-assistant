"""GitHub repository ingestion.

Clones a repository (shallow) into a temp directory, walks the file tree,
and turns every indexable file into a LlamaIndex Document. The temp
directory is always cleaned up afterwards.
"""

import os
import shutil
import tempfile
from pathlib import Path

from git import Repo
from llama_index.core import Document

from app.parsers.code import parse_code_file
from app.parsers.markdown import parse_markdown_file
from app.rag.ingestion import IGNORED_DIRS, is_indexable_file

# Regex-safe conversion: "https://github.com/owner/repo.git" -> "owner_repo".
def _repo_slug(repo_url: str) -> str:
    """Derive an 'owner_repo' slug from a GitHub URL for naming collections."""
    normalized = repo_url.rstrip("/").removesuffix(".git")
    parts = [p for p in normalized.split("/") if p]
    return "_".join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def collection_name_for_repo(repo_url: str) -> str:
    """ChromaDB collection name for a GitHub repo, e.g. `github_kubernetes_kubernetes`."""
    slug = _repo_slug(repo_url)
    # Collection names must be valid Chroma names: alnum, dash, underscore.
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in slug)
    return f"github_{slug}"


def clone_and_parse_repo(repo_url: str, branch: str | None = None) -> tuple[list[Document], dict]:
    """Clone the repo and parse every indexable file.

    Returns:
        (documents, stats) where stats contains file counts and the slug.
    """
    temp_dir = tempfile.mkdtemp(prefix="docsassist_")
    try:
        # Shallow clone keeps large repos fast.
        clone_kwargs = {"depth": 1}
        if branch:
            clone_kwargs["branch"] = branch
        Repo.clone_from(repo_url, temp_dir, **clone_kwargs)

        documents: list[Document] = []
        file_count = 0
        for root, dirs, files in os.walk(temp_dir):
            # Prune ignored directories in-place so os.walk skips them.
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for filename in files:
                full_path = os.path.join(root, filename)
                if not is_indexable_file(full_path):
                    continue
                rel_path = os.path.relpath(full_path, temp_dir)
                doc = _parse_any_file(full_path, rel_path, repo_url)
                if doc is not None:
                    documents.append(doc)
                    file_count += 1

        stats = {"slug": _repo_slug(repo_url), "files": file_count}
        return documents, stats
    finally:
        # Always clean up the cloned repo.
        shutil.rmtree(temp_dir, ignore_errors=True)


def _parse_any_file(full_path: str, rel_path: str, repo_url: str) -> Document | None:
    """Parse a single repo file, attaching repo context to its metadata."""
    ext = Path(full_path).suffix.lower()
    if ext == ".pdf":
        from app.parsers.pdf import extract_pdf

        try:
            text = extract_pdf(full_path)
        except Exception:
            return None
        if not text.strip():
            return None
        return Document(
            text=text,
            metadata={
                "file_path": rel_path,
                "repo": _repo_slug(repo_url),
                "source": repo_url,
                "source_type": "github",
                "file_type": "pdf",
            },
        )

    # Route by extension to the code or markdown parser.
    if ext in {".md", ".markdown", ".rst", ".txt"}:
        doc = parse_markdown_file(full_path)
    else:
        doc = parse_code_file(full_path)
    if doc is None:
        return None

    # Override metadata with the repo path rather than the temp path.
    doc.metadata["file_path"] = rel_path
    doc.metadata["repo"] = _repo_slug(repo_url)
    doc.metadata["source"] = repo_url
    doc.metadata["source_type"] = "github"
    return doc
