"""GitHub repository ingestion.

Clones a repository (shallow) into a temp directory, walks the file tree,
and turns every indexable file into a LlamaIndex Document. The temp
directory is always cleaned up afterwards.
"""

import os
import re
import shutil
import tempfile
from pathlib import Path

from git import Repo, exc as git_exc
from llama_index.core import Document

from app.parsers.code import parse_code_file
from app.parsers.markdown import parse_markdown_file
from app.rag.ingestion import IGNORED_DIRS, is_indexable_file

# Valid GitHub URL patterns: https://github.com/owner/repo[.git]
_GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+(/.*)?$"
)


def _validate_github_url(url: str) -> str | None:
    """Return a clean URL or None if invalid."""
    url = url.strip().rstrip("/")
    if not _GITHUB_URL_RE.match(url):
        return None
    # Remove trailing slashes and optional .git suffix for normalisation.
    return url.removesuffix(".git")


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

    Raises:
        ValueError: If the URL is invalid.
        RuntimeError: If cloning fails (not found, auth required, etc.).
    """
    clean_url = _validate_github_url(repo_url)
    if clean_url is None:
        raise ValueError(
            f"Invalid GitHub URL: {repo_url}. "
            "Expected format: https://github.com/owner/repo"
        )

    temp_dir = tempfile.mkdtemp(prefix="docsassist_")
    try:
        # Shallow clone keeps large repos fast.
        clone_kwargs = {"depth": 1}
        if branch:
            clone_kwargs["branch"] = branch
        Repo.clone_from(clean_url, temp_dir, **clone_kwargs)

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
                doc = _parse_any_file(full_path, rel_path, clean_url)
                if doc is not None:
                    documents.append(doc)
                    file_count += 1

        stats = {"slug": _repo_slug(clean_url), "files": file_count}
        return documents, stats
    except git_exc.GitCommandError as exc:
        # Git commands fail with specific error codes:
        # - 128: repository not found or requires authentication
        # - 129: invalid URL
        # - 1: various (e.g. branch not found)
        stderr = str(exc.stderr or "").strip().lower()
        if "repository not found" in stderr or "could not read from remote" in stderr:
            raise RuntimeError(
                f"Repository not found or requires authentication: {clean_url}. "
                "Make sure the repository is public and the URL is correct."
            ) from exc
        if "auth" in stderr or "could not read username" in stderr:
            raise RuntimeError(
                f"Authentication required for: {clean_url}. "
                "Private repositories require a GitHub token."
            ) from exc
        if "branch" in stderr or "couldn't find remote ref" in stderr:
            raise RuntimeError(
                f"Branch '{branch}' not found in: {clean_url}. "
                "Check the branch name and try again."
            ) from exc
        raise RuntimeError(f"Git clone failed: {exc}") from exc
    finally:
        # Always clean up the cloned repo.
        shutil.rmtree(temp_dir, ignore_errors=True)


def _parse_any_file(full_path: str, rel_path: str, repo_url: str) -> Document | None:
    """Parse a single repo file, attaching repo context to its metadata."""
    ext = Path(full_path).suffix.lower()
    # PDF files.
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

    # Extensionless documentation files (README, CHANGELOG, etc.).
    name = Path(full_path).name
    if not ext and name.upper() in {
        "README", "CHANGELOG", "CHANGES", "HISTORY", "LICENSE",
        "LICENSES", "CONTRIBUTING", "AUTHORS", "COPYING",
    }:
        doc = parse_markdown_file(full_path)
    elif ext in {".md", ".markdown", ".rst", ".txt"}:
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
