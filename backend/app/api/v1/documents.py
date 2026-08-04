"""Document API routes: index (upload / github / openapi), list, delete."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import (
    DocumentListResponse,
    DocumentMeta,
    GithubIndexRequest,
    OpenApiIndexRequest,
)
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentMeta)
async def upload_documents(files: list[UploadFile] = File(...)) -> dict:
    """Upload one or more files (markdown, code, PDF, text) to be indexed."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    try:
        return document_service.index_upload(files)
    except ConnectionError as exc:
        # Embedding provider unavailable — guide the user, don't dump a stack.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # Broad catch to surface user-facing ingestion errors.
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@router.post("/github", response_model=DocumentMeta)
async def github_document(req: GithubIndexRequest) -> dict:
    """Clone a GitHub repository and index all its indexable files."""
    try:
        return document_service.index_github(req.repo_url, branch=req.branch)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"GitHub ingestion failed: {exc}"
        ) from exc


@router.post("/openapi", response_model=DocumentMeta)
async def openapi_document(req: OpenApiIndexRequest) -> dict:
    """Fetch a Swagger/OpenAPI spec by URL and index it."""
    try:
        return document_service.index_openapi(req.spec_url)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"OpenAPI ingestion failed: {exc}"
        ) from exc


@router.get("", response_model=DocumentListResponse)
def list_docs() -> dict:
    """List all indexed documents."""
    return {"documents": [DocumentMeta(**d) for d in document_service.list_documents()]}


@router.delete("/{doc_id}", response_model=dict)
def delete_doc(doc_id: str) -> dict:
    """Delete an indexed document and its vectors."""
    deleted = document_service.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    return {"deleted": True}
