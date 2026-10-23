# Developer Documentation Assistant

RAG-powered chat app: index GitHub repos, Swagger specs, PDFs and Markdown files, then ask questions with cited answers.

## Architecture

```
backend/   FastAPI + LiteLLM + ChromaDB + LlamaIndex
frontend/  React 19 + TypeScript + Tailwind + Vite
data/      ChromaDB vectors + document registry (documents.json)
```

### Backend layout (`backend/app/`)
- `main.py` — FastAPI app, CORS, middleware wiring
- `config.py` — pydantic-settings (env vars / .env file)
- `middleware.py` — request logging + per-IP rate limiting
- `api/v1/` — route modules: `chat`, `conversations`, `documents`, `search`, `router`
- `models/schemas.py` — Pydantic request/response schemas (mirrored in `frontend/src/types/`)
- `rag/ingestion.py` — chunking (CodeSplitter / MarkdownNodeParser / SentenceSplitter) + ChromaDB upsert
- `rag/retrieval.py` — top-k semantic search across collections
- `rag/prompts.py` — system prompt + RAG prompt builder
- `services/chat_service.py` — in-memory conversation store, LiteLLM streaming, SSE event helpers
- `services/document_service.py` — orchestrates parsers → ingestion → registry
- `services/document_registry.py` — JSON-backed document metadata store (`data/documents.json`)
- `services/provider_service.py` — LLM provider detection + priority ordering
- `core/dependencies.py` — lazy ChromaDB client + embedding model singletons
- `parsers/` — github, markdown, openapi, pdf, code parsers

### Frontend layout (`frontend/src/`)
- `App.tsx` — root layout (sidebar + chat window)
- `lib/api.ts` — typed fetch wrappers for all backend endpoints
- `types/index.ts` — TypeScript interfaces mirroring Pydantic schemas
- `hooks/useChat.ts` — chat state, streaming, conversation management
- `hooks/useDocuments.ts` — document CRUD state
- `components/Chat/` — ChatWindow, MessageList, MessageBubble, Composer, ConversationHistory, CodeBlock
- `components/Documents/` — DocumentList, UploadPanel

## Running locally

```bash
# One-time setup
make setup              # creates venv + installs deps

# Copy and fill in at least one LLM key
cp backend/.env.example backend/.env

# Start backend (port 8000) and frontend (port 5173) separately:
make backend
make frontend

# Or both in one terminal (background processes):
make dev
```

The Vite dev server proxies `/api` to `http://localhost:8000` — use `http://localhost:5173` in the browser.

## Configuration (`backend/.env`)

There are two ways to connect an LLM. **Gateway mode** is preferred and takes
priority whenever `LLM_BASE_URL` is set.

### Gateway mode (recommended)

One OpenAI-compatible endpoint (e.g. a LiteLLM proxy) serves every model —
chat *and* embeddings — behind a single key. Any model id the gateway exposes
"just works"; the UI's provider dropdown is built by grouping the gateway's
`/models` catalog into logical providers (inferred from model-name prefixes).

| Variable | Default | Notes |
|---|---|---|
| `LLM_BASE_URL` | — | OpenAI-compatible endpoint incl. version path, e.g. `http://localhost:6655/litellm/v1`. Set this to enable gateway mode. |
| `LLM_API_KEY` | — | Virtual key the gateway requires |
| `LLM_MODEL` | `gpt-4o` | Default chat model when the client picks none (any catalog id) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model id exposed by the gateway |

### Direct mode (used only when `LLM_BASE_URL` is empty)

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI chat + embeddings |
| `ANTHROPIC_API_KEY` | — | Anthropic chat only (embeddings use OpenAI/Ollama) |
| `GEMINI_API_KEY` | — | Google Gemini chat (get key at aistudio.google.com) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama endpoint |
| `DEFAULT_PROVIDER` | `openai` | `openai \| anthropic \| gemini \| ollama` |
| `DEFAULT_MODEL` | `gpt-4o` | Model for the default provider |

### Shared

| Variable | Default | Notes |
|---|---|---|
| `CHROMA_PERSIST_DIR` | `../data/chroma` | Relative to `backend/` |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |
| `RATE_LIMIT_REQUESTS` | `60` | Requests per window per IP |

**Minimum requirement:** either `LLM_BASE_URL` + `LLM_API_KEY` (gateway), or one
of `OPENAI_API_KEY` / `GEMINI_API_KEY`, or a running Ollama server with a chat
model (`ollama pull llama3.1`) and embedding model (`ollama pull nomic-embed-text`).

## Testing

```bash
make test-backend       # pytest (uses fake embeddings, temp Chroma dir)
make test-frontend      # tsc build + oxlint
make test               # both
```

Tests inject a `FakeEmbedModel` via `conftest.py` and isolate ChromaDB to a `tmp_path` — no real API keys needed.

## Key conventions

- **ChromaDB collections:** one per indexed document; named after the doc ID (sanitised repo URL, `upload_<title>`, `openapi_<title>`).
- **Document registry:** `data/documents.json` stores display metadata. ChromaDB stores vectors. They're kept in sync by `document_service.py`.
- **Conversations:** in-memory only (dict keyed by `conv.id`). Lost on server restart — by design for local use.
- **SSE streaming:** `POST /api/v1/chat/stream` emits `{type: token|sources|error|done, ...}` events; the frontend drives rendering purely from these.
- **Provider fallback:** if the requested model/provider fails, the next available one is tried automatically (`provider_priority` in `provider_service.py`).
- **Embeddings:** in gateway mode, routed through `LLM_BASE_URL` using `EMBEDDING_MODEL`. In direct mode, OpenAI if `OPENAI_API_KEY` is set, else Ollama `nomic-embed-text`.
- **Any model "just works":** `litellm.drop_params = True` (set at startup) silently drops params a model rejects — e.g. reasoning models like gpt-5 that reject custom `temperature`.
- **Chunking:** code files use `CodeSplitter` (tree-sitter, 40 lines/chunk), markdown uses `MarkdownNodeParser` (heading-aware), everything else uses `SentenceSplitter` (512 tokens).
- **No test comments / docstring prose** — keep inline comments to non-obvious WHY, not WHAT.

## Common tasks

```bash
# Add a new parser for a file type
# → add parser in backend/app/parsers/
# → add extension mapping in ingestion.py CODE_LANGUAGES or MARKDOWN_EXTENSIONS
# → add a route in documents.py + service method in document_service.py

# Seed demo data (needs an embedding provider configured)
make seed

# Wipe vectors + registry to start fresh
make clean
```
