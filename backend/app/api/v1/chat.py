"""Chat API routes: non-streaming, streaming (SSE), and provider listing."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ProviderListResponse,
    ProviderInfo,
)
from app.services import chat_service
from app.services.provider_service import get_available_providers

router = APIRouter(tags=["chat"])


def _provider_error(exc: Exception) -> HTTPException:
    """Convert embedding/LLM connectivity errors into a 503 response."""
    return HTTPException(status_code=503, detail=str(exc))


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> dict:
    """Ask a question and get a complete, cited answer."""
    try:
        return chat_service.answer_query(
            query=req.query,
            provider=req.provider,
            model=req.model,
            conversation_id=req.conversation_id,
        )
    except (ConnectionError, RuntimeError) as exc:
        raise _provider_error(exc) from exc


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Ask a question and stream the answer over Server-Sent Events."""
    return StreamingResponse(
        chat_service.stream_answer(
            query=req.query,
            provider=req.provider,
            model=req.model,
            conversation_id=req.conversation_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/providers", response_model=ProviderListResponse)
def providers() -> dict:
    """List available LLM providers and whether each is configured/online."""
    return {"providers": [ProviderInfo(**p) for p in get_available_providers()]}
