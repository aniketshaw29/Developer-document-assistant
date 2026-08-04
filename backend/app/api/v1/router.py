"""Aggregates all /api/v1 sub-routers into a single router.

Each feature module (chat, documents, search) exposes an `APIRouter`
that gets included here. Mounted in `app.main` under the `/api/v1` prefix.
"""

from fastapi import APIRouter

from app.api.v1 import chat, conversations, documents, search

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(documents.router)
api_router.include_router(search.router)
