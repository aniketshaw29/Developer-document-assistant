"""Chat service — RAG answer generation and streaming.

Combines retrieval (top-k chunks from ChromaDB) with the LLM prompt
template, then streams tokens back to the client. Conversation history
is kept in memory keyed by conversation_id.
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator

from app.config import settings
from app.core.dependencies import list_collections
from app.rag.prompts import SYSTEM_PROMPT, build_rag_prompt
from app.rag.retrieval import RetrievedChunk, retrieve
from app.services.provider_service import resolve_model, validate_provider

# In-memory conversation store: conversation_id -> list of chat messages.
# Simple dict is fine for Phase 1; swap for Redis in a later phase.
_conversations: dict[str, list[dict]] = {}


def new_conversation() -> str:
    """Create an empty conversation and return its id."""
    conv_id = uuid.uuid4().hex[:12]
    _conversations[conv_id] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    return conv_id


def get_or_create_conversation(conversation_id: str | None) -> tuple[str, list[dict]]:
    """Return (conversation_id, messages), creating a conversation if needed."""
    if conversation_id and conversation_id in _conversations:
        return conversation_id, _conversations[conversation_id]
    return new_conversation(), _conversations[new_conversation()]


def _litellm_model_string(provider: str, model: str | None) -> str:
    """Prefix model with provider for LiteLLM routing where needed.

    OpenAI and Anthropic models are passed through as-is; Ollama needs
    the `ollama/` prefix plus the base URL.
    """
    if provider == "ollama":
        base = resolve_model(provider, model)
        # resolve_model already adds the prefix for ollama defaults.
        return base if base.startswith("ollama/") else f"ollama/{base}"
    return resolve_model(provider, model)


def _litellm_kwargs(provider: str) -> dict:
    """Extra kwargs for LiteLLM per provider (API keys / base URLs)."""
    kwargs: dict = {}
    if provider == "ollama":
        kwargs["api_base"] = settings.ollama_base_url
    elif provider == "openai" and settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    elif provider == "anthropic" and settings.anthropic_api_key:
        kwargs["api_key"] = settings.anthropic_api_key
    return kwargs


def _sources_to_dict(chunks: list[RetrievedChunk]) -> list[dict]:
    """Convert retrieved chunks into the JSON shape the UI expects."""
    return [
        {
            "file_path": chunk.file_path,
            "text": chunk.text,
            "score": round(chunk.score, 4),
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]


def answer_query(
    query: str,
    provider: str | None = None,
    conversation_id: str | None = None,
    collection_names: list[str] | None = None,
) -> dict:
    """Non-streaming answer: retrieve context, ask the LLM, return JSON."""
    # Retrieve the most relevant chunks from the indexed docs.
    chunks = retrieve(query, collection_names=collection_names, n_results=10)

    conv_id, messages = get_or_create_conversation(conversation_id)
    if not chunks:
        # No indexed docs — fall back to a plain answer without context.
        messages.append({"role": "user", "content": query})
        answer = "I don't have any indexed documentation yet. Upload files or index a repo first."
    else:
        user_message = build_rag_prompt(query, [c.text for c in chunks])
        messages.append({"role": "user", "content": user_message})
        answer = _generate(messages, provider)

    # Keep the assistant turn in history and return a trimmed user message.
    messages.append({"role": "assistant", "content": answer})
    return {
        "answer": answer,
        "sources": _sources_to_dict(chunks),
        "conversation_id": conv_id,
    }


def _generate(messages: list[dict], provider: str | None) -> str:
    """Call the LLM (synchronously) via LiteLLM and return the full text."""
    import litellm

    provider = validate_provider(provider)
    model = _litellm_model_string(provider, None)
    kwargs = _litellm_kwargs(provider)

    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=0.2,
        **kwargs,
    )
    return response.choices[0].message.content or ""


async def stream_answer(
    query: str,
    provider: str | None = None,
    conversation_id: str | None = None,
    collection_names: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Yield SSE event JSON strings for a streaming RAG answer.

    Events: {type: token, content} ... {type: sources, ...} {type: done}.
    """
    import litellm

    try:
        chunks = retrieve(query, collection_names=collection_names, n_results=10)
    except ConnectionError as exc:
        yield _event("error", str(exc))
        yield _event("done")
        return

    conv_id, messages = get_or_create_conversation(conversation_id)

    if not chunks:
        answer = "I don't have any indexed documentation yet. Upload files or index a repo first."
        yield _event("token", answer)
        yield _event("sources", sources=[])
        yield _event("done", conversation_id=conv_id)
        return

    user_message = build_rag_prompt(query, [c.text for c in chunks])
    messages.append({"role": "user", "content": user_message})

    try:
        provider = validate_provider(provider)
    except RuntimeError as exc:
        yield _event("error", str(exc))
        yield _event("done", conversation_id=conv_id)
        return
    model = _litellm_model_string(provider, None)
    kwargs = _litellm_kwargs(provider)

    # Stream the LLM response token by token.
    stream = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=0.2,
        stream=True,
        **kwargs,
    )

    full_text = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else ""
        if delta:
            full_text += delta
            yield _event("token", delta)

    messages.append({"role": "assistant", "content": full_text})
    yield _event("sources", sources=_sources_to_dict(chunks))
    yield _event("done", conversation_id=conv_id)


def _event(
    event_type: str, content: str = "", sources: list[dict] | None = None, conversation_id: str = ""
) -> str:
    """Build a single SSE `data:` payload string."""
    payload: dict = {"type": event_type, "content": content}
    if sources is not None:
        payload["sources"] = sources
    if conversation_id:
        payload["conversation_id"] = conversation_id
    return f"data: {json.dumps(payload)}\n\n"


def search_raw(query: str, n_results: int = 10) -> dict:
    """Raw retrieval endpoint for debugging."""
    chunks = retrieve(query, n_results=n_results)
    return {"results": _sources_to_dict(chunks)}
