/**
 * Shared TypeScript types for the documentation assistant.
 * These mirror the Pydantic schemas exposed by the FastAPI backend.
 */

/** A source chunk used to answer a question (citation). */
export interface Source {
  /** File path or endpoint path the chunk came from. */
  file_path: string;
  /** Short preview of the chunk text. */
  text: string;
  /** Relevance / similarity score, higher is better. */
  score: number;
  /** Metadata attached to the chunk (repo, language, etc.). */
  metadata: Record<string, unknown>;
}

/** A single chat message in the UI. */
export interface Message {
  /** Client-generated id used for React keys. */
  id: string;
  /** Role of the message author. */
  role: 'user' | 'assistant';
  /** Message content (markdown for assistant messages). */
  content: string;
  /** Citations attached to an assistant answer. */
  sources?: Source[];
  /** True while the assistant is still streaming this message. */
  isStreaming?: boolean;
  /** Set when generation failed for this message. */
  error?: string;
}

/** Metadata about an indexed document (returned by GET /documents). */
export interface DocumentMeta {
  /** Unique document id (also the ChromaDB collection name). */
  id: string;
  /** Human-friendly title. */
  title: string;
  /** Source type: github | openapi | upload. */
  source_type: string;
  /** Original URL for github/openapi documents (used for re-indexing). */
  source?: string;
  /** Number of files indexed. */
  files_indexed: number;
  /** Number of chunks created. */
  chunks_created: number;
  /** ISO timestamp of when the document was indexed. */
  created_at: string;
}

/** Request body for POST /chat and POST /chat/stream. */
export interface ChatRequest {
  query: string;
  provider?: string;
  /** Optional model override for the selected provider. */
  model?: string;
  conversation_id?: string;
}

/** Structured response for POST /chat. */
export interface ChatResponse {
  answer: string;
  sources: Source[];
  conversation_id: string;
}

/** SSE event types streamed by POST /chat/stream. */
export type StreamEventType = 'token' | 'sources' | 'error' | 'done';

/** A single Server-Sent Event from the streaming endpoint. */
export interface StreamEvent {
  type: StreamEventType;
  content: string;
  sources?: Source[];
  conversation_id?: string;
}

/** Available LLM provider info from GET /providers. */
export interface ProviderInfo {
  name: string;
  available: boolean;
  /** Default model for this provider. */
  model?: string;
  /** Selectable models (e.g. all pulled Ollama models). */
  models?: string[];
}

/** Lightweight conversation entry for the history sidebar. */
export interface ConversationSummary {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

/** A full conversation including its message history. */
export interface ConversationDetail {
  id: string;
  title: string;
  /** History messages (system prompt excluded) with role + content. */
  messages: { role: string; content: string }[];
  created_at: string;
  updated_at: string;
}
