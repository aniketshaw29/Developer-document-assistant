"""Aggregates all /api/v1 sub-routers into a single router.

Each feature module (chat, documents, search) exposes an `APIRouter`
that gets included here. Mounted in `app.main` under the `/api/v1` prefix.
"""

from fastapi import APIRouter

api_router = APIRouter()
