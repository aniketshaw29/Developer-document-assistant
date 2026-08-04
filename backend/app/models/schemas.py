"""Pydantic request/response schemas for the API.

These mirror the shapes consumed by the React frontend (see
`frontend/src/types/index.ts`).
"""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Body for POST /chat and POST /chat/stream."""

    query: str = Field(..., min_length=1, description="The user's question")
    provider: str | None = Field(None, description="openai | anthropic | ollama")
    conversation_id: str | None = Field(None, description="Resume a conversation")


class Source(BaseModel):
    """A citation: which indexed chunk backed part of the answer."""

    file_path: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    answer: str
    sources: list[Source] = Field(default_factory=list)
    conversation_id: str


class GithubIndexRequest(BaseModel):
    """Body for POST /documents/github."""

    repo_url: str = Field(..., description="GitHub repository URL, e.g. https://github.com/kubernetes/kubernetes")
    branch: str | None = Field(None, description="Optional branch/tag to clone")


class OpenApiIndexRequest(BaseModel):
    """Body for POST /documents/openapi."""

    spec_url: str = Field(..., description="URL to a Swagger/OpenAPI spec (JSON or YAML)")


class DocumentMeta(BaseModel):
    """Metadata for an indexed document."""

    id: str
    title: str
    source_type: str
    files_indexed: int
    chunks_created: int
    created_at: str


class DocumentListResponse(BaseModel):
    """Response body for GET /documents."""

    documents: list[DocumentMeta]


class SearchRequest(BaseModel):
    """Body for POST /search (raw retrieval for debugging)."""

    query: str = Field(..., min_length=1)
    n_results: int = Field(10, ge=1, le=50)


class SearchResponse(BaseModel):
    """Response body for POST /search."""

    results: list[Source]


class ProviderInfo(BaseModel):
    """Status of a single LLM provider."""

    name: str
    available: bool
    model: str | None = None


class ProviderListResponse(BaseModel):
    """Response body for GET /providers."""

    providers: list[ProviderInfo]
