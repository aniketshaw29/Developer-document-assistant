"""Application configuration loaded from environment variables / .env file.

Uses pydantic-settings so all settings are validated and type-checked at startup.
Create a `.env` file next to this module (see `.env.example`) to override defaults.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory of the backend package (parent of the `app` package).
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central application settings.

    Every field maps to an environment variable with the same name
    (e.g. `OPENAI_API_KEY` -> `settings.OPENAI_API_KEY`).
    """

    # === LLM providers ===
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # === Default provider / model ===
    default_provider: str = "openai"  # openai | anthropic | ollama
    default_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # === Storage ===
    # ChromaDB persistence directory, resolved relative to the backend dir.
    chroma_persist_dir: str = "../data/chroma"

    # === Server ===
    cors_origins: str = "http://localhost:5173"
    log_level: str = "info"

    # === Rate limiting ===
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def chroma_persist_path(self) -> Path:
        """Absolute path to the ChromaDB persistence directory."""
        return (BACKEND_DIR / self.chroma_persist_dir).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins parsed from the comma-separated setting."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Module-level singleton so all imports share one settings object.
settings = Settings()
