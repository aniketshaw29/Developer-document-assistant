"""LLM provider abstraction.

Wraps LiteLLM so the chat pipeline can use OpenAI, Anthropic or local
Ollama interchangeably. Embeddings stay on OpenAI (or Ollama when no key
is configured) regardless of the chat provider, since Anthropic does not
ship an embedding API.
"""

import httpx

from app.config import settings

# Provider -> default model name used when the client does not pick one.
PROVIDER_DEFAULTS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "ollama": "llama3.1",
}


def _ollama_models_available() -> bool:
    """Return True if an Ollama server is reachable and lists models."""
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return len(models) > 0
    except Exception:
        return False


def get_available_providers() -> list[dict]:
    """Return provider info with availability status for the settings panel."""
    providers = [
        {
            "name": "openai",
            "available": bool(settings.openai_api_key),
            "model": settings.default_model if settings.default_provider == "openai"
            else PROVIDER_DEFAULTS["openai"],
        },
        {
            "name": "anthropic",
            "available": bool(settings.anthropic_api_key),
            "model": PROVIDER_DEFAULTS["anthropic"],
        },
        {
            "name": "ollama",
            "available": _ollama_models_available(),
            "model": PROVIDER_DEFAULTS["ollama"],
        },
    ]
    return providers


def resolve_model(provider: str, model: str | None) -> str:
    """Resolve the effective model string for a provider.

    Ollama models are prefixed with the provider so LiteLLM routes them.
    """
    if model:
        return model
    default = PROVIDER_DEFAULTS.get(provider)
    if provider == "ollama":
        return f"ollama/{default}"
    return default or "gpt-4o"


class NoProviderAvailableError(RuntimeError):
    """Raised when no LLM provider is configured/reachable."""


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
    raise NoProviderAvailableError(
        "No LLM provider is configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
        "in backend/.env, or start Ollama (ollama serve && ollama pull llama3.1)."
    )
