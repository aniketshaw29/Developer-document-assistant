# Architecture

## System Overview

```
┌─────────────┐     SSE Stream      ┌──────────────────┐
│   React UI  │ ◄──────────────────► │   FastAPI Server  │
│  (Vite/TS)  │     REST API        │   (Uvicorn)       │
└─────────────┘                      └──────┬───────────┘
                                            │
                              ┌─────────────┼─────────────┐
                              │             │             │
                        ┌─────▼─────┐ ┌─────▼─────┐ ┌────▼──────┐
                        │ LlamaIndex│ │ LiteLLM   │ │ ChromaDB  │
                        │  RAG Core │ │ (Router)  │ │ (Vectors) │
                        └─────┬─────┘ └─────┬─────┘ └───────────┘
                              │             │
                              │      ┌──────▼──────┐
                              │      │  LLM APIs   │
                              │      │ OpenAI      │
                              │      │ Anthropic   │
                              │      │ Ollama      │
                              │      └─────────────┘
                        ┌─────▼─────┐
                        │  Parsers  │
                        │ GitHub    │
                        │ OpenAPI   │
                        │ PDF       │
                        │ Code      │
                        └───────────┘
```

## Data Flow

### Ingestion Flow
```
User submits source (URL/file)
    │
    ▼
API Router (documents.py)
    │
    ▼
DocumentService → detects source type
    │
    ├── GitHub URL → GithubParser (clone, walk, filter)
    ├── OpenAPI URL → OpenAPIParser (fetch, convert to markdown)
    ├── PDF upload → PDFParser (PyMuPDF text extraction)
    └── Code files → CodeParser (extension detection, read)
    │
    ▼
LlamaIndex IngestionPipeline
    ├── Text splitting (SentenceSplitter / CodeSplitter)
    ├── Metadata extraction (title, source, type)
    └── Embedding (via LiteLLM → provider)
    │
    ▼
ChromaDB (upsert with metadata)
```

### Query Flow
```
User asks question
    │
    ▼
API Router (chat.py)
    │
    ▼
ChatService
    ├── Embed query → ChromaDB.similarity_search(n=10)
    ├── Build context from top-k chunks
    ├── Construct RAG prompt with context + citations
    └── Stream response via LiteLLM
    │
    ▼
SSE Stream → React UI → MessageBubble + SourcesPanel
```

## Component Details

### Backend Services

**ChatService** (`services/chat_service.py`)
- Manages conversation state (in-memory dict, keyed by conversation_id)
- Builds RAG context from retrieved chunks
- Streams tokens via LiteLLM's `acompletion`
- Returns structured sources alongside answers

**DocumentService** (`services/document_service.py`)
- Orchestrates ingestion: parse → chunk → embed → store
- Tracks document metadata (source URL, file count, chunk count, timestamp)
- Handles deduplication (re-indexing same source replaces old data)
- Manages ChromaDB collection lifecycle

**ProviderService** (`services/provider_service.py`)
- Wraps LiteLLM for provider switching
- Validates API keys per provider
- Returns available providers list
- Handles fallback logic

### RAG Pipeline

**IngestionPipeline** (LlamaIndex)
```
Input Documents
    → SentenceSplitter(chunk_size=512, overlap=50)
    → TitleExtractor (LLM-powered)
    → OpenAIEmbedding / provider-specific embedding
    → ChromaDB VectorStore
```

**QueryEngine**
```
Query
    → Embed query
    → ChromaDB.query(n_results=10, metadata_filters)
    → Build context string from top chunks
    → Apply RAG prompt template
    → Stream LLM response
    → Attach source citations
```

### Frontend Components

**ChatWindow.tsx** — Main layout
- Sidebar: document list + upload panel
- Main area: message list + composer
- Handles SSE streaming, maintains message state

**MessageBubble.tsx** — Single message
- Renders markdown content (using react-markdown)
- Shows citation badges linking to SourcesPanel
- Distinguishes user vs assistant messages

**SourcesPanel.tsx** — Citation sidebar
- Expandable panel showing source chunks used in answer
- Each source shows: file path, chunk text preview, relevance score
- Click to highlight source in document list

**Composer.tsx** — Input area
- Text input with Enter to send, Shift+Enter for newline
- Provider selector dropdown
- Loading state during streaming

### State Management

React state with hooks (no Redux needed for this scope):

```typescript
// useChat hook
interface ChatState {
  messages: Message[];
  conversationId: string | null;
  isStreaming: boolean;
  currentProvider: string;
}

// useDocuments hook
interface DocumentsState {
  documents: DocumentMeta[];
  isUploading: boolean;
  uploadProgress: number;
}
```

## Error Handling

| Error Type | Backend | Frontend |
|---|---|---|
| Invalid API key | 400 + descriptive message | Toast notification |
| Provider unavailable | 503 + fallback suggestion | Provider switch prompt |
| Empty query | 422 validation error | Inline form error |
| Ingestion failure | 500 + error details | Upload retry button |
| Rate limit | 429 + retry-after | Auto-retry with backoff |
