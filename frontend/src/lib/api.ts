import type {
  ChatRequest,
  ChatResponse,
  DocumentMeta,
  ProviderInfo,
} from '../types';

const BASE_URL = '/api/v1';

/**
 * Thin fetch wrapper for the FastAPI backend.
 * Throws an Error with the server-provided detail message on failure.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // Keep the status text if the body is not JSON.
    }
    throw new Error(`${res.status}: ${detail}`);
  }

  return res.json() as Promise<T>;
}

/** Send a chat message and get the full (non-streaming) answer. */
export function sendChat(req: ChatRequest): Promise<ChatResponse> {
  return request('/chat', { method: 'POST', body: JSON.stringify(req) });
}

/** Upload one or more files to be indexed. */
export async function uploadFiles(files: File[]): Promise<DocumentMeta> {
  const form = new FormData();
  for (const file of files) {
    form.append('files', file);
  }

  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // Keep the status text if the body is not JSON.
    }
    throw new Error(`${res.status}: ${detail}`);
  }

  return res.json() as Promise<DocumentMeta>;
}

/** Index a GitHub repository by URL. */
export function indexGithub(repoUrl: string): Promise<DocumentMeta> {
  return request('/documents/github', {
    method: 'POST',
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

/** Index a Swagger/OpenAPI spec by URL. */
export function indexOpenApi(specUrl: string): Promise<DocumentMeta> {
  return request('/documents/openapi', {
    method: 'POST',
    body: JSON.stringify({ spec_url: specUrl }),
  });
}

/** List all indexed documents. */
export function listDocuments(): Promise<{ documents: DocumentMeta[] }> {
  return request('/documents');
}

/** Re-index an existing document from its stored source URL. */
export function reindexDocument(id: string): Promise<DocumentMeta> {
  return request(`/documents/${id}/reindex`, { method: 'POST' });
}

/** Delete an indexed document. */
export function deleteDocument(id: string): Promise<{ deleted: boolean }> {
  return request(`/documents/${id}`, { method: 'DELETE' });
}

/** List available LLM providers and their status. */
export function listProviders(): Promise<{ providers: ProviderInfo[] }> {
  return request('/providers');
}

/**
 * Stream a chat response over Server-Sent Events.
 * Calls `onEvent` for each parsed event; resolves when the stream ends.
 */
export async function streamChat(
  req: ChatRequest,
  onEvent: (event: import('../types').StreamEvent) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok || !res.body) {
    throw new Error(`${res.status}: ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by blank lines.
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';

    for (const raw of events) {
      for (const line of raw.split('\n')) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6);
          if (payload === '[DONE]') return;
          onEvent(JSON.parse(payload) as import('../types').StreamEvent);
        }
      }
    }
  }
}
