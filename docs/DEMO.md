# Demo Script

A step-by-step walkthrough for showing off the Developer Documentation
Assistant — to a recruiter, interviewer, or at a meetup. It covers both
the UI flow and the raw API (useful for screenshots and gifs).

---

## 0. Prerequisites

- Backend running: `make backend` (see `SETUP.md` for the env config).
- Frontend running: `make frontend` → open http://localhost:5173.
- At least one LLM provider: OpenAI/Anthropic key **or** Ollama running
  locally. Embeddings are OpenAI or Ollama (`ollama pull nomic-embed-text`).

## 1. Seed realistic data (2 minutes)

```bash
make seed
```

This indexes:

1. The **Swagger Petstore** OpenAPI 3 spec (all endpoints, schemas, paths).
2. The **AWS Lambda developer guide** repo (hundreds of markdown pages).

Both appear in the "Indexed documents" sidebar. You can also point it at
your own sources:

```bash
SEED_REPO=https://github.com/kubernetes/website SEED_SPEC= make seed
```

## 2. UI walkthrough (live demo)

### Ingestion

1. Open the app. In the sidebar, switch to the **OpenAPI** tab, paste
   `https://petstore3.swagger.io/api/v3/openapi.json`, click **Index**.
   Watch the loading state.
2. Switch to **GitHub**, paste
   `https://github.com/awsdocs/aws-lambda-developer-guide`, click **Index**.
   This takes ~30–60s — good moment to mention tree-sitter chunking.
3. Point out the **re-index** button (circular arrow) on each document and
   the per-source badges (purple = GitHub, green = OpenAPI).

### Chatting with citations

4. In the composer, pick **Auto** or a specific provider/model from the
   dropdown (Ollama works fully offline).
5. Ask: *"How do I create a pet?"* → answer cites the Petstore `POST /pet`
   endpoint.
6. Ask: *"How do I set up a Lambda function from a zip?"* → answer cites the
   AWS docs repo.
7. Click the **N sources ▾** link under the answer to expand the citations,
   then hover the copy button on any code block.

### Provider switching + fallback

8. If you have multiple providers configured, switch models mid-chat from
   the dropdown. The status dots in the sidebar footer show what's live.
9. Explain the fallback: if the selected provider errors, the app
   transparently retries the next available one.

### Conversation history

10. Ask a follow-up ("…and how do I delete it?"), then click **New chat**.
11. Open **Chat history** in the sidebar and click the previous
    conversation — it resumes exactly where you left off.

### Polish features

12. Toggle **dark mode** (moon/sun in the sidebar header).
13. Resize the window narrow → the sidebar becomes a slide-in drawer with a
    hamburger menu. Good for the "responsive" talking point.

## 3. API-level demo (curl)

Even without the UI, every feature is scriptable — great for a README gif:

```bash
BASE=http://localhost:8000/api/v1

# Providers
curl -s $BASE/providers | python3 -m json.tool

# Index a GitHub repo
curl -s -X POST $BASE/documents/github \
  -H 'Content-Type: application/json' \
  -d '{"repo_url":"https://github.com/awsdocs/aws-lambda-developer-guide"}' | python3 -m json.tool

# Index an OpenAPI spec
curl -s -X POST $BASE/documents/openapi \
  -H 'Content-Type: application/json' \
  -d '{"spec_url":"https://petstore3.swagger.io/api/v3/openapi.json"}' | python3 -m json.tool

# Stream a chat answer (SSE) — curl shows the raw events
curl -sN -X POST $BASE/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"query":"How do I create a pet?","conversation_id":null}'

# Conversation history
curl -s $BASE/conversations | python3 -m json.tool
```

## 4. Suggested GitHub description & topics

> **Description:** ChatGPT for your codebases. Index GitHub repos,
> Swagger/OpenAPI specs, PDFs and markdown — then ask questions and get
> answers with source citations. FastAPI + LlamaIndex + ChromaDB + React.
> Supports OpenAI, Anthropic, and local Ollama with automatic provider
> fallback.

> **Topics:** `rag`, `llm`, `fastapi`, `llamaindex`, `chromadb`,
> `openai`, `anthropic`, `ollama`, `react`, `typescript`, `documentation`,
> `chatgpt`, `semantic-search`, `retrieval-augmented-generation`,
> `tree-sitter`, `server-sent-events`, `portfolio`
