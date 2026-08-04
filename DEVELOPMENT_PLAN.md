# Development Plan

A concrete, ordered build guide for implementing the Developer Documentation Assistant. Follow this sequence — each step builds on the previous one and ends in a working, testable state.

**Reference docs:** `PLAN.md`, `ARCHITECTURE.md`, `INGESTION.md`, `ROADMAP.md`, `SETUP.md`

---

## Step 0 — Project Scaffolding (0.5 day)

### 0.1 Repo root
- [ ] Create `backend/`, `frontend/`, `data/`, `data/.gitkeep`
- [ ] Create `.gitignore`:
  - Python: `venv/`, `__pycache__/`, `*.pyc`, `.env`, `.pytest_cache/`
  - Node: `node_modules/`, `dist/`, `build/`
  - Data: `data/chroma/`
  - OS: `.DS_Store`
- [ ] Create `backend/.env.example` and root `.env.example`

### 0.2 Backend skeleton
- [ ] `backend/requirements.txt` (from `SETUP.md`)
- [ ] Create package structure with `__init__.py` files:
  ```
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── api/__init__.py
  │   ├── api/v1/__init__.py
  │   ├── core/__init__.py
  │   ├── rag/__init__.py
  │   ├── models/__init__.py
  │   ├── services/__init__.py
  │   └── parsers/__init__.py
  └── tests/__init__.py
  ```
- [ ] `config.py` — Pydantic Settings class loading from `.env`
- [ ] `main.py` — empty FastAPI app with CORS, health check at `/health`

### 0.3 Frontend skeleton
- [ ] Scaffold Vite + React + TypeScript + Tailwind:
  ```bash
  npm create vite@latest frontend -- --template react-ts
  cd frontend && npm install && npm install -D tailwindcss@3 autoprefixer postcss
  npx tailwindcss init -p
  ```
- [ ] Configure `vite.config.ts` proxy: `/api` → `http://localhost:8000`
- [ ] Tailwind config + `index.css` directives
- [ ] `src/types/index.ts` — TypeScript interfaces (Message, Source, DocumentMeta, etc.)

### Verification
- [ ] Backend: `uvicorn app.main:app --reload` → `/health` returns ok
- [ ] Frontend: `npm run dev` → Vite serves at 5173, proxy works

---

## Step 1 — Vector Store + Ingestion Core (1 day)

### 1.1 ChromaDB integration
- [ ] `core/dependencies.py` — `get_chroma_client()` (PersistentClient at `data/chroma`)
- [ ] `core/dependencies.py` — `get_collection(name)` (get_or_create with cosine space)
- [ ] Collection naming helpers per `INGESTION.md` conventions

### 1.2 LlamaIndex pipeline
- [ ] `rag/ingestion.py`:
  - `build_pipeline(embed_model)` → IngestionPipeline with SentenceSplitter
  - `ingest_documents(docs, collection_name)` → parse → chunk → embed → upsert
  - `delete_collection(collection_name)`
- [ ] Embedding model factory: OpenAI embeddings (default) with configurable model
- [ ] `rag/prompts.py` — system prompt + RAG context template

### Verification
- [ ] Unit test: ingest 2 small markdown files → verify chunks exist in ChromaDB
- [ ] Unit test: re-ingest same file → no duplicate IDs (idempotent)

---

## Step 2 — Parsers (1 day)

### 2.1 `parsers/pdf.py`
- [ ] `extract_pdf(file_path) -> str` using PyMuPDF, page markers included

### 2.2 `parsers/code.py`
- [ ] Extension detection → CodeSplitter config per language
- [ ] `parse_code_file(path) -> List[Document]`

### 2.3 `parsers/openapi.py`
- [ ] Fetch spec via httpx (YAML/JSON auto-detect)
- [ ] `openapi_to_markdown(spec) -> str` per `INGESTION.md` spec
- [ ] `parse_openapi_url(url) -> Document`

### 2.4 `parsers/github.py`
- [ ] `gitpython` clone to temp dir (shallow, `--depth 1`)
- [ ] Walk tree, skip ignored dirs, filter by extension
- [ ] Route each file to correct parser (code/markdown/config)
- [ ] Cleanup temp dir in `finally`

### Verification
- [ ] Test each parser with a fixture file
- [ ] Test: clone a small public repo, confirm file counts

---

## Step 3 — Services (1 day)

### 3.1 `services/document_service.py`
- [ ] `index_github(repo_url)` → collection name `github_{owner}_{repo}`, returns doc_id + stats
- [ ] `index_upload(files)` → per-file collection or grouped, returns stats
- [ ] `index_openapi(spec_url)` → returns stats
- [ ] `list_documents()` / `delete_document(doc_id)` — track metadata in ChromaDB `metadata` or a JSON index file

### 3.2 `services/chat_service.py`
- [ ] `retrieve(query, collection_names, n)` → top-k chunks with metadata
- [ ] `generate_answer(query, sources, provider)` → non-streaming RAG response
- [ ] `stream_answer(query, sources, provider)` → async generator yielding tokens
- [ ] In-memory conversation store: `{conversation_id: [messages]}`

### 3.3 `services/provider_service.py`
- [ ] `get_available_providers()` → openai/anthropic/ollama with key status
- [ ] `get_llm(provider, model)` → LiteLLM-backed instance
- [ ] `get_embed_model(provider)` → embeddings per provider (OpenAI default)

### Verification
- [ ] Manual: index a fixture → retrieve → answer via curl

---

## Step 4 — API Routes (0.5 day)

### 4.1 `api/v1/documents.py`
- [ ] `POST /documents/upload` — multipart files
- [ ] `POST /documents/github` — { repo_url, branch? }
- [ ] `POST /documents/openapi` — { spec_url }
- [ ] `GET /documents` — list
- [ ] `DELETE /documents/{doc_id}`
- [ ] `POST /documents/ingest-status/{doc_id}` — long-running ingestion progress (Phase 2)

### 4.2 `api/v1/chat.py`
- [ ] `POST /chat` — JSON, returns answer + sources
- [ ] `POST /chat/stream` — SSE stream (token/sources/done events)

### 4.3 `api/v1/search.py`
- [ ] `POST /search` — raw retrieval for debugging

### 4.4 `api/v1/router.py`
- [ ] Aggregate all v1 routers

### Verification
- [ ] Every endpoint smoke-tested with curl
- [ ] `/docs` (Swagger UI) shows all endpoints

---

## Step 5 — Frontend Chat UI (1 day)

### 5.1 Core chat
- [ ] `lib/api.ts` — typed fetch wrapper
- [ ] `lib/stream.ts` — SSE reader (from `ARCHITECTURE.md`)
- [ ] `hooks/useChat.ts` — messages, streaming, conversationId
- [ ] `components/Chat/ChatWindow.tsx` — layout: sidebar + message area
- [ ] `components/Chat/MessageList.tsx` — scroll, auto-scroll on new token
- [ ] `components/Chat/MessageBubble.tsx` — react-markdown rendering
- [ ] `components/Chat/Composer.tsx` — input, Enter to send, disabled while streaming

### 5.2 Documents
- [ ] `hooks/useDocuments.ts` — CRUD + ingestion
- [ ] `components/Documents/UploadPanel.tsx` — drag-and-drop files
- [ ] `components/Documents/DocumentList.tsx` — list + delete + re-index

### Verification
- [ ] Upload a markdown file → ask a question → streaming answer with markdown rendering

---

## Step 6 — GitHub + OpenAPI Ingestion UI (0.5 day)

- [ ] `UploadPanel` tabs: Files / GitHub URL / OpenAPI URL
- [ ] Loading states during long ingestion (30-60s)
- [ ] Document metadata display (source, files, chunks)
- [ ] Re-index button

### Verification
- [ ] Index a real GitHub repo (e.g., a small public repo) and query it

---

## Step 7 — Multi-Provider (1 day)

### 7.1 Backend
- [ ] `GET /providers` — list with status
- [ ] LiteLLM wired for chat streaming (`litellm.acompletion` with fallbacks)
- [ ] Ollama support: auto-detect local models via `GET /api/tags`
- [ ] Embedding fallback: if OpenAI key missing and Ollama running, use Ollama embeddings

### 7.2 Frontend
- [ ] `components/Settings/ProviderSelector.tsx` — dropdown in composer
- [ ] API key entry (stored in backend config, not shipped)
- [ ] Provider status indicator

### Verification
- [ ] Chat works with OpenAI key set
- [ ] Chat works with Ollama (fully local, zero keys)

---

## Step 8 — Sources Panel + Polish (1 day)

### 8.1 Sources
- [ ] `components/Sources/SourcesPanel.tsx` — expandable citations per answer
- [ ] Each source: file_path, chunk preview, relevance score
- [ ] Backend returns structured sources in both `/chat` and `/chat/stream` final event

### 8.2 Polish
- [ ] Dark mode
- [ ] Responsive layout
- [ ] Empty states + loading skeletons
- [ ] Error toasts
- [ ] Rate limiting middleware (basic in-memory)
- [ ] Request logging middleware

### Verification
- [ ] Full manual walkthrough: index → chat → citations → delete → re-index

---

## Step 9 — Tests, Docs, Demo (1 day)

### 9.1 Tests (pytest)
- [ ] `tests/test_parsers.py` — pdf, code, openapi converters
- [ ] `tests/test_documents.py` — ingestion idempotency, deletion
- [ ] `tests/test_chat.py` — retrieval + answer (mocked LLM)

### 9.2 Documentation
- [ ] `README.md` — badges, architecture diagram, quick start, API reference, screenshots
- [ ] `.env.example` with comments
- [ ] `Makefile` — `make dev`, `make install`, `make test`

### 9.3 Demo
- [ ] Seed a real doc set (Spring Boot or Kubernetes docs subset)
- [ ] Record demo GIF
- [ ] Push to GitHub with tags/topics

---

## Execution Order (Dependency Graph)

```
Step 0 ──► Step 1 ──► Step 2 ──► Step 3 ──► Step 4 ──► Step 5 ──► Step 6
                  │                                        │
                  └────────── Step 7 ◄──────────────────────┘
                                          │
                                   Step 8 ──► Step 9
```

Steps 0-4 are backend-only. Step 5 is the first frontend milestone and depends only on Steps 0-4. Step 7 (multi-provider) is independent of Step 6 and can be parallelized.

**Time estimate:** ~7 working days total. Phases map to `ROADMAP.md`: Steps 0-5 → Phase 1, Step 6 → Phase 2, Step 7 → Phase 3, Steps 8-9 → Phase 4.

## Definition of Done

- Every endpoint in `PLAN.md` exists and is smoke-tested
- Both streaming and non-streaming chat work with cited sources
- Three ingestion sources working: upload, GitHub, OpenAPI
- At least two LLM providers working (OpenAI + Ollama)
- `pytest` suite passes
- README with screenshots + architecture diagram complete
- Demo recorded and repo pushed
