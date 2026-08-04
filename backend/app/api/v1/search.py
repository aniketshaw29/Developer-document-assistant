"""Search API route: raw retrieval for debugging and testing."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import SearchRequest, SearchResponse
from app.services.chat_service import search_raw

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> dict:
    """Return raw top-k retrieval results for a query (no LLM involved)."""
    try:
        return search_raw(req.query, n_results=req.n_results)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
