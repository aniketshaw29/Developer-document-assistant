"""Conversation history API routes: list, get, delete."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
)
from app.services import chat_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
def list_conversations() -> dict:
    """List all in-memory conversations, newest first."""
    return {
        "conversations": [
            ConversationSummary(**c) for c in chat_service.list_conversations()
        ]
    }


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str) -> dict:
    """Return a conversation's messages so the UI can resume it."""
    conv = chat_service.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}", response_model=dict)
def delete_conversation(conversation_id: str) -> dict:
    """Delete a conversation."""
    if not chat_service.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}
