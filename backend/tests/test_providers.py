"""Tests for provider selection, model override, and fallback logic.

LLM calls are mocked at the LiteLLM layer so the fallback behaviour can
be verified without any real provider.
"""

from types import SimpleNamespace

import pytest

from app.services import chat_service
from app.services.provider_service import provider_priority


def test_provider_priority_orders_requested_first(monkeypatch):
    """The requested provider wins, then the default, then the rest."""
    monkeypatch.setattr(
        "app.services.provider_service.get_available_providers",
        lambda: [
            {"name": "openai", "available": True},
            {"name": "anthropic", "available": True},
            {"name": "ollama", "available": True},
        ],
    )
    assert provider_priority("ollama") == ["ollama", "openai", "anthropic"]


def test_provider_priority_skips_unavailable(monkeypatch):
    """Unavailable providers never appear in the candidate list."""
    monkeypatch.setattr(
        "app.services.provider_service.get_available_providers",
        lambda: [
            {"name": "openai", "available": False},
            {"name": "ollama", "available": True},
        ],
    )
    assert provider_priority(None) == ["ollama"]


def test_provider_priority_raises_when_none_available(monkeypatch):
    """No available providers raises a clear user-facing error."""
    monkeypatch.setattr(
        "app.services.provider_service.get_available_providers",
        lambda: [
            {"name": "openai", "available": False},
            {"name": "anthropic", "available": False},
            {"name": "ollama", "available": False},
        ],
    )
    with pytest.raises(RuntimeError, match="No LLM provider"):
        provider_priority(None)


def test_generate_falls_back_when_first_provider_fails(monkeypatch):
    """A failing provider falls back to the next available one."""
    calls = []
    import litellm

    def completion(model, messages, temperature, **kwargs):
        calls.append(model)
        if "gpt" in model or "openai" in model:
            raise RuntimeError("OpenAI rate limited")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    monkeypatch.setattr(litellm, "completion", completion)
    monkeypatch.setattr(
        "app.services.provider_service.get_available_providers",
        lambda: [
            {"name": "openai", "available": True, "model": "gpt-4o"},
            {"name": "ollama", "available": True, "model": "llama3.1"},
        ],
    )

    # Force the default provider to openai so it is tried before ollama.
    monkeypatch.setattr("app.config.settings.default_provider", "openai")

    result = chat_service._generate([{"role": "user", "content": "hi"}], "openai")
    assert result == "ok"
    # First call was openai (failed), second was ollama (succeeded).
    assert calls[0] == "gpt-4o"
    assert calls[1] == "ollama/llama3.1"


def test_generate_uses_requested_model_override(monkeypatch):
    """An explicit model override is passed straight to LiteLLM."""
    import litellm

    seen = {}

    def completion(model, messages, temperature, **kwargs):
        seen["model"] = model
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))]
        )

    monkeypatch.setattr(litellm, "completion", completion)
    monkeypatch.setattr(
        "app.services.provider_service.get_available_providers",
        lambda: [{"name": "openai", "available": True, "model": "gpt-4o"}],
    )

    chat_service._generate([{"role": "user", "content": "hi"}], "openai", model="gpt-4o-mini")
    assert seen["model"] == "gpt-4o-mini"


def test_generate_raises_when_all_providers_fail(monkeypatch):
    """When every provider fails, a clear RuntimeError is raised."""
    import litellm

    monkeypatch.setattr(
        litellm,
        "completion",
        lambda model, messages, temperature, **kwargs: (_ for _ in ()).throw(
            RuntimeError("bad key")
        ),
    )
    monkeypatch.setattr(
        "app.services.provider_service.get_available_providers",
        lambda: [{"name": "openai", "available": True, "model": "gpt-4o"}],
    )

    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        chat_service._generate([{"role": "user", "content": "hi"}], "openai")


def test_gateway_mode_routes_model_through_endpoint(monkeypatch):
    """In gateway mode every model goes through the OpenAI-compatible endpoint."""
    import litellm
    from app.config import settings

    monkeypatch.setattr(settings, "llm_base_url", "http://gw.local/v1")
    monkeypatch.setattr(settings, "llm_api_key", "vk-123")

    seen = {}

    def completion(model, messages, temperature, **kwargs):
        seen["model"] = model
        seen["api_base"] = kwargs.get("api_base")
        seen["api_key"] = kwargs.get("api_key")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
        )

    monkeypatch.setattr(litellm, "completion", completion)
    monkeypatch.setattr(
        "app.services.provider_service.get_available_providers",
        lambda: [{"name": "gemini", "available": True, "model": "gemini-2.5-flash"}],
    )

    result = chat_service._generate(
        [{"role": "user", "content": "hi"}], "gemini", model="gemini-2.5-flash"
    )
    assert result == "ok"
    # Model id is used verbatim behind the openai/ prefix; creds come from the gateway.
    assert seen["model"] == "openai/gemini-2.5-flash"
    assert seen["api_base"] == "http://gw.local/v1"
    assert seen["api_key"] == "vk-123"


def test_gateway_mode_groups_models_by_inferred_provider(monkeypatch):
    """The gateway catalog is grouped into logical providers for the UI."""
    from app.config import settings
    from app.services import provider_service as ps

    monkeypatch.setattr(settings, "llm_base_url", "http://gw.local/v1")
    monkeypatch.setattr(
        ps,
        "gateway_models",
        lambda: [
            "gpt-5",
            "anthropic--claude-4.6-sonnet",
            "gemini-2.5-flash",
            "text-embedding-3-small",  # embedding — excluded from chat list
        ],
    )

    providers = {p["name"]: p for p in ps.get_available_providers()}
    assert set(providers) == {"openai", "anthropic", "gemini"}
    assert all(p["available"] for p in providers.values())
    # Embedding model must not appear as a selectable chat model.
    all_models = [m for p in providers.values() for m in p["models"]]
    assert "text-embedding-3-small" not in all_models
