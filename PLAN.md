# Developer Documentation Assistant — Project Plan

## Vision
A ChatGPT-like interface that indexes your documentation (GitHub repos, Swagger specs, PDFs, READMEs) and lets you ask natural language questions with cited answers.

## Goals
- **Portfolio showcase** — polished UI, impressive demo, strong README
- **Multi-source ingestion** — GitHub repos, file uploads, Swagger URLs, PDFs
- **Multi-provider LLM** — OpenAI, Anthropic, Ollama (local) via LiteLLM
- **RAG-powered answers** — not just chat, but grounded retrieval with source citations

## Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Backend | FastAPI + Uvicorn | 0.115+ | Async API server with SSE streaming |
| RAG Framework | LlamaIndex | 0.14.x | Ingestion pipelines, retrieval, query engine |
| LLM Abstraction | LiteLLM | 1.40+ | Multi-provider unified interface |
| Vector Database | ChromaDB | 0.5+ | Embedding storage and similarity search |
| PDF Parsing | PyMuPDF (fitz) | latest | Fast text extraction from PDFs |
| Code Parsing | LlamaIndex CodeSplitter | built-in | tree-sitter AST-aware chunking |
| Frontend | React + Vite + TypeScript | React 18+ | SPA with chat interface |
| Styling | Tailwind CSS | 3.4+ | Utility-first CSS |
| Streaming | SSE (EventSource) | native | Real-time token streaming |
| Chat History | In-memory (Phase 1), Redis (Phase 2) | — | Session persistence |
| Python Version | 3.11+ | — | Required for LlamaIndex |
| Node Version | 20+ | — | Required for Vite |

## Project Structure

```
Developer-document-assistant/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app, CORS, lifespan
│   │   ├── config.py                  # Pydantic Settings (.env loading)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py          # Aggregates all v1 routes
│   │   │       ├── chat.py            # POST /chat, POST /chat/stream
│   │   │       ├── documents.py       # POST/GET/DELETE /documents
│   │   │       └── search.py          # POST /search (raw retrieval)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py        # get_llm(), get_vector_store(), etc.
│   │   │   ├── exceptions.py          # Custom exception classes + handlers
│   │   │   └── middleware.py          # CORS, logging, rate limiting
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py           # Document parsing, chunking, embedding
│   │   │   ├── retrieval.py           # Query engine setup, retrieval config
│   │   │   └── prompts.py            # System prompts, RAG prompt templates
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py            # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── chat_service.py        # Chat + streaming logic
│   │   │   ├── document_service.py    # Upload, parse, index pipeline
│   │   │   └── provider_service.py    # LLM provider switching
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── github.py              # Clone + walk repo files
│   │       ├── openapi.py             # Swagger/OpenAPI → Markdown converter
│   │       ├── pdf.py                 # PDF text extraction
│   │       └── code.py                # Code file detection + parsing
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_chat.py
│   │   ├── test_documents.py
│   │   └── test_parsers.py
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── index.css                  # Tailwind directives
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   │   ├── ChatWindow.tsx     # Main chat layout
│   │   │   │   ├── MessageList.tsx    # Scrollable message history
│   │   │   │   ├── MessageBubble.tsx  # Single message + citations
│   │   │   │   └── Composer.tsx       # Input with send button
│   │   │   ├── Sources/
│   │   │   │   └── SourcesPanel.tsx   # Expandable citation sidebar
│   │   │   ├── Documents/
│   │   │   │   ├── UploadPanel.tsx    # Drag-and-drop + URL input
│   │   │   │   └── DocumentList.tsx   # Indexed docs with delete
│   │   │   └── Settings/
│   │   │       └── ProviderSelector.tsx  # LLM provider dropdown
│   │   ├── lib/
│   │   │   ├── api.ts                 # Fetch wrapper for FastAPI
│   │   │   └── stream.ts             # SSE streaming helper
│   │   ├── hooks/
│   │   │   ├── useChat.ts            # Chat state + streaming
│   │   │   └── useDocuments.ts       # Document CRUD
│   │   └── types/
│   │       └── index.ts              # TypeScript interfaces
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── postcss.config.js
├── data/
│   └── .gitkeep                       # ChromaDB persistent storage
├── README.md
├── .gitignore
├── .env.example
└── Makefile                           # Convenience commands
```

## API Design

### Chat Endpoints

```
POST /api/v1/chat
  Body: { query: string, provider?: string, conversation_id?: string }
  Response: { answer: string, sources: Source[], conversation_id: string }

POST /api/v1/chat/stream
  Body: { query: string, provider?: string, conversation_id?: string }
  Response: SSE stream of { type: "token"|"sources"|"done", content: string, sources?: Source[] }
```

### Document Endpoints

```
POST /api/v1/documents/github
  Body: { repo_url: string, branch?: string }
  Response: { doc_id: string, files_indexed: int, chunks_created: int }

POST /api/v1/documents/upload
  Body: multipart/form-data (files)
  Response: { doc_id: string, files_indexed: int, chunks_created: int }

POST /api/v1/documents/openapi
  Body: { spec_url: string }
  Response: { doc_id: string, endpoints_indexed: int, chunks_created: int }

GET /api/v1/documents
  Response: { documents: DocumentMeta[] }

DELETE /api/v1/documents/{doc_id}
  Response: { deleted: bool }
```

### Search Endpoint (for debugging/testing)

```
POST /api/v1/search
  Body: { query: string, n_results?: int }
  Response: { results: SearchResult[] }
```

## Key Design Decisions

1. **LlamaIndex over LangChain**: Purpose-built for document RAG. Better ingestion pipelines, metadata extraction, and retrieval primitives. 15-20% lower latency for pure RAG workloads.

2. **LiteLLM for provider abstraction**: Single function signature for 100+ providers. Built-in fallback routing and cost tracking. No vendor lock-in.

3. **ChromaDB embedded mode**: Zero-config persistent storage. Good for <10M vectors. Metadata filtering for source-scoped queries.

4. **SSE over WebSocket**: Unidirectional token streaming is all we need. Simpler, native browser support, no connection management.

5. **Separate ingestion parsers**: Each source type (GitHub, OpenAPI, PDF, code) gets its own parser module. Easy to add new sources without touching the core pipeline.
