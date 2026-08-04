"""FastAPI application entrypoint.

Creates the FastAPI app, wires up CORS, mounts the v1 API router, and
provides a health-check endpoint. Run with:

    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks.

    Currently a placeholder; used later to lazily initialise the
    vector store, LLM clients, etc.
    """
    logging.basicConfig(level=settings.log_level.upper())
    logging.getLogger("uvicorn").info("Developer Documentation Assistant starting up...")
    yield
    logging.getLogger("uvicorn").info("Shutting down...")


app = FastAPI(
    title="Developer Documentation Assistant",
    description=(
        "ChatGPT for your codebases. Index GitHub repos, Swagger specs, PDFs "
        "and READMEs, then ask questions with cited answers."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the React dev server (and any configured origin) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Simple liveness probe for orchestrators and smoke tests."""
    return {"status": "ok"}


# Imported after app creation to avoid circular imports.
from app.api.v1.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
