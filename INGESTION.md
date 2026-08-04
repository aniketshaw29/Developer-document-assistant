# Document Ingestion Pipeline

## Source Types

### 1. GitHub Repositories

**Flow:**
```
repo_url → git clone → walk file tree → filter by extension → parse → chunk → embed → store
```

**Implementation:**
- Clone to temp directory using `gitpython`
- Walk tree, skip `.git/`, `node_modules/`, `__pycache__/`, `venv/`
- Filter by extension:
  - **Code** (`.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`): CodeSplitter with tree-sitter
  - **Docs** (`.md`, `.rst`, `.txt`): MarkdownNodeParser
  - **Config** (`.yaml`, `.json`, `.toml`): SentenceSplitter
  - **Ignore**: binary files, images, lock files

**Metadata per chunk:**
```python
{
    "source": "github",
    "repo": "owner/repo",
    "file_path": "src/api/handlers.py",
    "language": "python",
    "file_type": "code",
    "line_start": 42,
    "line_end": 67,
    "chunk_index": 3
}
```

**Chunking strategy:**
- Code files: CodeSplitter(chunk_lines=40, overlap=15, max_chars=1500)
- Markdown files: MarkdownNodeParser (splits on headings)
- Config files: SentenceSplitter(chunk_size=512, overlap=50)

**Cleanup:** Delete temp directory after ingestion.

### 2. File Uploads

**Supported formats:**
- `.md` — MarkdownNodeParser
- `.txt` — SentenceSplitter
- `.pdf` — PyMuPDF text extraction → SentenceSplitter
- `.py`, `.js`, `.ts`, etc. — CodeSplitter
- `.yaml`, `.json` — SentenceSplitter

**Flow:**
```
Upload via multipart/form-data → detect extension → route to parser → chunk → embed → store
```

**Metadata per chunk:**
```python
{
    "source": "upload",
    "filename": "architecture.md",
    "file_type": "markdown",
    "chunk_index": 0,
    "uploaded_at": "2026-08-04T12:00:00Z"
}
```

**PDF handling (PyMuPDF):**
```python
import fitz  # PyMuPDF

def extract_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    text_parts = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
    doc.close()
    return "\n\n".join(text_parts)
```

### 3. Swagger/OpenAPI URLs

**Flow:**
```
spec_url → fetch YAML/JSON → parse structure → convert to markdown → chunk → embed → store
```

**Conversion logic (~80 lines):**
```python
def openapi_to_markdown(spec: dict) -> str:
    parts = []
    info = spec.get("info", {})
    parts.append(f"# {info.get('title', 'API Documentation')}\n")
    parts.append(f"Version: {info.get('version', 'unknown')}\n")
    parts.append(info.get("description", "") + "\n")

    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            parts.append(f"\n## {method.upper()} `{path}`\n")
            if summary := details.get("summary"):
                parts.append(f"**Summary:** {summary}\n")
            if desc := details.get("description"):
                parts.append(f"{desc}\n")
            # Parameters
            if params := details.get("parameters"):
                parts.append("**Parameters:**\n")
                for p in params:
                    parts.append(f"- `{p.get('name')}` ({p.get('in')}, {p.get('schema', {}).get('type', 'any')}): {p.get('description', '')}\n")
            # Request body
            if req_body := details.get("requestBody"):
                parts.append("**Request Body:**\n")
                content = req_body.get("content", {})
                for media_type, schema_info in content.items():
                    parts.append(f"- Content-Type: `{media_type}`\n")
                    if schema := schema_info.get("schema", {}).get("$ref"):
                        parts.append(f"  Schema: `{schema.split('/')[-1]}`\n")
            # Responses
            if responses := details.get("responses"):
                parts.append("**Responses:**\n")
                for status, resp in responses.items():
                    parts.append(f"- `{status}`: {resp.get('description', '')}\n")

    # Schemas
    if schemas := spec.get("components", {}).get("schemas", {}):
        parts.append("\n## Data Models\n")
        for name, schema in schemas.items():
            parts.append(f"\n### {name}\n")
            if props := schema.get("properties"):
                for prop_name, prop_info in props.items():
                    parts.append(f"- `{prop_name}` ({prop_info.get('type', 'any')}): {prop_info.get('description', '')}\n")

    return "\n".join(parts)
```

**Metadata per chunk:**
```python
{
    "source": "openapi",
    "spec_title": "My API",
    "method": "POST",
    "path": "/api/v1/orders",
    "section": "endpoint",
    "chunk_index": 0
}
```

### 4. Code Files (standalone)

Same as GitHub repo code parsing but for individual uploaded files. Uses the same CodeSplitter with tree-sitter.

**Supported languages (tree-sitter):**
Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, Ruby, PHP, Swift, Kotlin, Scala, Haskell, Lua, Bash, SQL

## Embedding Configuration

```python
# OpenAI (default)
embed_model = "text-embedding-3-small"  # 1536 dimensions, cheapest

# Anthropic (via LiteLLM)
# Anthropic doesn't have embeddings — use OpenAI embeddings as default

# Ollama (local)
embed_model = "nomic-embed-text"  # Local, free, 768 dimensions
```

**Important:** Embedding model is pinned per ChromaDB collection. Switching embedding models requires creating a new collection and re-embedding all documents.

## Deduplication Strategy

- **GitHub repos:** Collection named `github_{owner}_{repo}`. Re-indexing replaces entire collection.
- **Uploads:** Document ID = SHA256 of filename + content hash. Upsert prevents duplicates.
- **OpenAPI:** Collection named `openapi_{spec_title_hash}`. Re-indexing replaces entire collection.

## Collection Naming Convention

```
github_{owner}_{repo}        # e.g., github_kubernetes_kubernetes
upload_{doc_id}              # e.g., upload_a1b2c3d4
openapi_{spec_hash}          # e.g., openapi_e5f6g7h8
```
