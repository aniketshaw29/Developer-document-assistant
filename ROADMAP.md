# Roadmap

## Phase 1 — MVP Core (Week 1-2)

**Goal:** Working RAG chat with file upload, single provider, basic UI.

### Backend
- [ ] FastAPI app scaffolding (main.py, config.py, CORS)
- [ ] Pydantic Settings with .env loading
- [ ] ChromaDB integration (PersistentClient, collection management)
- [ ] LlamaIndex ingestion pipeline (SentenceSplitter + embeddings)
- [ ] Query engine with RAG prompt template
- [ ] Chat endpoint (POST /chat) with source citations
- [ ] SSE streaming endpoint (POST /chat/stream)
- [ ] File upload endpoint (POST /documents/upload)
- [ ] Document list/delete endpoints
- [ ] PDF parser (PyMuPDF)
- [ ] Markdown parser (MarkdownNodeParser)
- [ ] Code file parser (CodeSplitter)
- [ ] System prompt for "documentation assistant" persona

### Frontend
- [ ] React + Vite + TypeScript + Tailwind scaffolding
- [ ] ChatWindow component (message list + composer)
- [ ] MessageBubble component (markdown rendering)
- [ ] Composer component (input + send)
- [ ] SSE streaming integration (useChat hook)
- [ ] File upload panel (drag-and-drop)
- [ ] Document list sidebar
- [ ] Basic error handling (toast notifications)

### Deliverable
- Upload files → ask questions → get cited answers from uploaded docs

---

## Phase 2 — Multi-Source Ingestion (Week 3)

**Goal:** Support GitHub repos, Swagger/OpenAPI URLs, PDF uploads.

### Backend
- [ ] GitHub parser (gitpython clone + file walker)
- [ ] GitHub clone endpoint (POST /documents/github)
- [ ] OpenAPI parser (YAML/JSON → markdown converter)
- [ ] OpenAPI endpoint (POST /documents/openapi)
- [ ] URL-based fetch for remote OpenAPI specs
- [ ] Improved metadata extraction (titles, source tracking)
- [ ] Deduplication logic for re-indexing

### Frontend
- [ ] GitHub URL input field in upload panel
- [ ] OpenAPI URL input field in upload panel
- [ ] Document metadata display (source type, file count, chunk count)
- [ ] Re-index button per document
- [ ] Loading states for ingestion (can take 30-60s for large repos)

### Deliverable
- Paste a GitHub URL → index the repo → ask questions about the codebase
- Paste a Swagger URL → index the API → ask about endpoints

---

## Phase 3 — Multi-Provider (Week 4)

**Goal:** Switch between OpenAI, Anthropic, and Ollama from the UI.

### Backend
- [x] LiteLLM integration (replace direct OpenAI calls)
- [x] Provider configuration (API keys per provider)
- [ ] Provider switching endpoint (POST /providers/set)
- [x] Ollama support (local model detection + pulled-model listing)
- [x] Fallback logic (if provider fails, try next)
- [x] Embedding model fallback (OpenAI embeddings, else local Ollama)

### Frontend
- [x] Provider selector dropdown in composer (per provider + model)
- [ ] Settings page/modal for API key configuration
- [x] Provider status indicators (connected/error dots)
- [x] Model name display per provider

### Deliverable
- Toggle between GPT-4, Claude, and local LLaMA from the UI
- Works without any API key using Ollama (fully local)

---

## Phase 4 — Polish & Showcase (Week 5)

**Goal:** Portfolio-ready project with impressive demo, documentation, and UX.

### Backend
- [x] Conversation history (in-memory, keyed by conversation_id)
- [x] Rate limiting middleware
- [x] Request logging middleware
- [x] Health check endpoint
- [x] OpenAPI docs at /docs (FastAPI auto-generated)

### Frontend
- [x] Sources panel (collapsible citation list per answer)
- [x] Conversation history sidebar (resume + delete)
- [x] Dark mode support (with OS-preference default)
- [x] Responsive layout (mobile drawer sidebar)
- [x] Keyboard shortcuts (Enter send, Escape clear input)
- [x] Markdown syntax highlighting in code blocks (with copy button)
- [x] Empty state illustrations
- [x] Loading skeleton animations

### Documentation
- [x] README.md with:
  - [x] Project description + screenshots (screenshots pending)
  - [x] Architecture diagram (ASCII)
  - [x] Quick start guide
  - [x] API reference
  - [x] Tech stack badges
  - [x] Contributing section
- [x] .gitignore
- [x] .env.example with comments
- [x] Makefile with dev commands (incl. `make seed`)

### Demo Prep
- [x] Seed with real documentation (`make seed` — Petstore + AWS Lambda guide)
- [ ] Record demo GIF or video
- [x] Demo script (`docs/DEMO.md`) + suggested GitHub description/topics

---

## Future (Post-MVP)

- [ ] Redis for chat history persistence
- [ ] Docker Compose for one-command deployment
- [ ] User authentication
- [ ] Multi-tenant support
- [ ] Webhook ingestion (auto-re-index on push)
- [ ] Slack/Discord bot integration
- [ ] Evaluation pipeline (RAGAS metrics)
- [ ] Caching layer (Redis) for repeated queries
