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
    "anthropic": "claude-sonnet-5-5",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.1",
}


def _ollama_models_available() -> bool:
    """Return True if an Ollama server is reachable and lists models."""
    return len(_ollama_models()) > 0


def _ollama_models() -> list[str]:
    """Return the names of models pulled on the local Ollama server."""
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
        resp.raise_for_status()
        return [m.get("name", "") for m in resp.json().get("models", []) if m.get("name")]
    except Exception:
        return []


def get_available_providers() -> list[dict]:
    """Return provider info with availability status for the settings panel."""
    ollama_models = _ollama_models()
    providers = [
        {
            "name": "openai",
            "available": bool(settings.openai_api_key),
            "model": settings.default_model if settings.default_provider == "openai"
            else PROVIDER_DEFAULTS["openai"],
            "models": [
                settings.default_model if settings.default_provider == "openai"
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
    return providers


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
    for name in ("openai", "anthropic", "gemini", "ollama"):
        if name in available and name not in ordered:
            ordered.append(name)
    if not ordered:
        raise NoProviderAvailableError(
            "No LLM provider is configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
            "in backend/.env, or start Ollama (ollama serve && ollama pull llama3.1)."
        )
    return ordered


def resolve_model(provider: str, model: str | None) -> str:
    """Resolve the effective model string for a provider.

    Ollama and Gemini models are prefixed with the provider so LiteLLM routes them.
    """
    if model:
        return model
    default = PROVIDER_DEFAULTS.get(provider)
    if provider == "ollama":
        return f"ollama/{default}"
    if provider == "gemini":
        return f"gemini/{default}"
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
