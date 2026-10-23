"""LLM provider abstraction.

Two modes:

* Gateway mode (``settings.llm_base_url`` set) — every chat and embedding
  call is routed through one OpenAI-compatible endpoint (e.g. a LiteLLM
  proxy). The gateway's ``/models`` catalog is surfaced to the UI, grouped
  into logical providers inferred from each model's name. Any model the
  gateway exposes works, whatever its underlying provider.

* Direct mode (``llm_base_url`` empty) — falls back to per-provider SDKs
  using the individual API keys (OpenAI / Anthropic / Gemini / local Ollama).
"""

import functools
import time

import httpx

from app.config import settings

# Provider -> default model name used in direct mode when none is picked.
PROVIDER_DEFAULTS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-5-5",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.1",
}

# Substrings used to group gateway model ids into logical providers for the UI.
# Checked in order; first match wins.
_PROVIDER_PATTERNS = (
    ("anthropic", ("anthropic", "claude")),
    ("gemini", ("gemini", "gemma")),
    ("openai", ("gpt-", "gpt_", "o1", "o3", "o4")),
    ("perplexity", ("sonar",)),
)

# Model ids that are embedding-only — excluded from the chat model list.
_EMBEDDING_HINTS = ("embedding", "embed")


class NoProviderAvailableError(RuntimeError):
    """Raised when no LLM provider is configured/reachable."""


def _infer_provider(model_id: str) -> str:
    """Group a gateway model id into a logical provider name for the UI."""
    lowered = model_id.lower()
    for name, hints in _PROVIDER_PATTERNS:
        if any(hint in lowered for hint in hints):
            return name
    return "other"


def _is_embedding_model(model_id: str) -> bool:
    """True if the model id looks like an embedding model (not for chat)."""
    lowered = model_id.lower()
    return any(hint in lowered for hint in _EMBEDDING_HINTS)


def _gateway_cache_key() -> int:
    """Coarse 30s time bucket so the gateway catalog is cached briefly."""
    return int(time.monotonic() // 30)


@functools.lru_cache(maxsize=4)
def _gateway_models_cached(cache_key: int) -> tuple[str, ...]:
    """Fetch and cache the gateway's model-id catalog (30s TTL via cache_key)."""
    try:
        headers = {}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        resp = httpx.get(
            f"{settings.llm_base_url.rstrip('/')}/models", headers=headers, timeout=5.0
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return tuple(m["id"] for m in data if m.get("id"))
    except Exception:
        return ()


def gateway_models() -> list[str]:
    """Return every model id the gateway exposes (chat + embeddings)."""
    return list(_gateway_models_cached(_gateway_cache_key()))


def gateway_chat_models() -> list[str]:
    """Return gateway model ids usable for chat (embeddings excluded)."""
    return [m for m in gateway_models() if not _is_embedding_model(m)]


def _ollama_models() -> list[str]:
    """Return the names of models pulled on the local Ollama server."""
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
        return [m.get("name", "") for m in resp.json().get("models", []) if m.get("name")]
    except Exception:
        return []


def _gateway_providers() -> list[dict]:
    """Build the provider list for the UI from the gateway catalog.

    Groups chat models by inferred provider so the Composer can render one
    optgroup per provider, each listing its models.
    """
    grouped: dict[str, list[str]] = {}
    for model_id in gateway_chat_models():
        grouped.setdefault(_infer_provider(model_id), []).append(model_id)

    providers: list[dict] = []
    for name, models in sorted(grouped.items()):
        models.sort()
        # Prefer the configured default model as this group's headline when present.
        default = settings.llm_model if settings.llm_model in models else models[0]
        providers.append(
            {
                "name": name,
                "available": True,
                "model": default,
                "models": models,
            }
        )
    return providers


def _direct_providers() -> list[dict]:
    """Build the provider list for direct (per-SDK) mode."""
    ollama_models = _ollama_models()
    return [
        {
            "name": "openai",
            "available": bool(settings.openai_api_key),
            "model": settings.default_model
            if settings.default_provider == "openai"
            else PROVIDER_DEFAULTS["openai"],
            "models": [
                settings.default_model
                if settings.default_provider == "openai"
                else PROVIDER_DEFAULTS["openai"]
            ],
        },
        {
            "name": "anthropic",
            "available": bool(settings.anthropic_api_key),
            "model": PROVIDER_DEFAULTS["anthropic"],
            "models": [PROVIDER_DEFAULTS["anthropic"]],
        },
        {
            "name": "gemini",
            "available": bool(settings.gemini_api_key),
            "model": PROVIDER_DEFAULTS["gemini"],
            "models": [PROVIDER_DEFAULTS["gemini"]],
        },
        {
            "name": "ollama",
            "available": len(ollama_models) > 0,
            "model": PROVIDER_DEFAULTS["ollama"],
            "models": ollama_models or [PROVIDER_DEFAULTS["ollama"]],
        },
    ]


def get_available_providers() -> list[dict]:
    """Return provider info with availability status for the settings panel."""
    if settings.gateway_enabled:
        return _gateway_providers()
    return _direct_providers()


def provider_priority(provider: str | None) -> list[str]:
    """Order in which providers should be tried, most preferred first.

    Used for fallback: the explicitly requested provider wins, then the
    configured default, then any remaining available providers.
    """
    available = {p["name"] for p in get_available_providers() if p["available"]}
    ordered: list[str] = []
    for candidate in (provider, settings.default_provider):
        if candidate in available and candidate not in ordered:
            ordered.append(candidate)
    for name in sorted(available):
        if name not in ordered:
            ordered.append(name)
    if not ordered:
        raise NoProviderAvailableError(_no_provider_message())
    return ordered


def resolve_model(provider: str, model: str | None) -> str:
    """Resolve the effective model string for a provider (direct mode only).

    Ollama and Gemini models are prefixed with the provider so LiteLLM routes
    them. In gateway mode, callers use the model id verbatim instead.
    """
    if model:
        return model
    default = PROVIDER_DEFAULTS.get(provider)
    if provider == "ollama":
        return f"ollama/{default}"
    if provider == "gemini":
        return f"gemini/{default}"
    return default or "gpt-4o"


def validate_provider(provider: str | None) -> str:
    """Return a usable provider name, or raise if none is configured.

    Prefers the requested provider, then the configured default, then any
    provider that is actually available.
    """
    available = {p["name"]: p["available"] for p in get_available_providers()}
    if provider and available.get(provider):
        return provider
    if available.get(settings.default_provider):
        return settings.default_provider
    for name, is_available in available.items():
        if is_available:
            return name
    raise NoProviderAvailableError(_no_provider_message())


def _no_provider_message() -> str:
    """Actionable error text tailored to the configured mode."""
    if settings.gateway_enabled:
        return (
            f"LLM gateway at {settings.llm_base_url} returned no models. "
            "Check that the proxy is running and LLM_API_KEY is valid."
        )
    return (
        "No LLM provider is configured. Set LLM_BASE_URL + LLM_API_KEY to use a "
        "gateway, or set OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY in "
        "backend/.env, or start Ollama (ollama serve && ollama pull llama3.1)."
    )
