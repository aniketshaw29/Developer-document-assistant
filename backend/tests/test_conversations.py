"""Tests for conversation history endpoints and rate limiting."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_conversation() -> str:
    """Drive a chat request far enough to create a conversation.

    Returns the conversation_id. Chat itself may 200/503 depending on the
    embedding provider, but the conversation record is created either way
    for a no-chunks (empty index) answer.
    """
    resp = client.post(
        "/api/v1/chat",
        json={"query": "how do I configure kafka retry?", "conversation_id": None},
    )
    assert resp.status_code in (200, 503)
    return resp.json().get("conversation_id")


def test_conversation_list_and_detail():
    """List, get, and delete conversation endpoints work end to end."""
    conv_id = _create_conversation()
    assert conv_id, "chat request did not return a conversation_id"

    listing = client.get("/api/v1/conversations")
    assert listing.status_code == 200
    summaries = listing.json()["conversations"]
    assert any(c["id"] == conv_id for c in summaries)
    entry = next(c for c in summaries if c["id"] == conv_id)
    assert entry["title"]
    assert entry["message_count"] >= 1

    detail = client.get(f"/api/v1/conversations/{conv_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == conv_id
    assert any(m["role"] == "user" for m in body["messages"])

    deleted = client.delete(f"/api/v1/conversations/{conv_id}")
    assert deleted.status_code == 200

    gone = client.get(f"/api/v1/conversations/{conv_id}")
    assert gone.status_code == 404


def test_conversation_not_found():
    """Unknown conversation ids return 404."""
    assert client.get("/api/v1/conversations/nope").status_code == 404
    assert client.delete("/api/v1/conversations/nope").status_code == 404


def test_rate_limiting_returns_429():
    """A low limit triggers 429 responses with a Retry-After header."""
    from fastapi import FastAPI

    from app.middleware import RateLimitMiddleware

    # Standalone app so we don't disturb the shared test client.
    limited = FastAPI()
    limited.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)

    @limited.get("/api/v1/documents")
    def docs():
        return {"documents": []}

    lc = TestClient(limited)
    ok = 0
    blocked = 0
    for _ in range(5):
        resp = lc.get("/api/v1/documents")
        if resp.status_code == 200:
            ok += 1
        elif resp.status_code == 429:
            blocked += 1
            assert resp.headers.get("Retry-After")
        else:
            raise AssertionError(f"unexpected status {resp.status_code}")

    assert ok == 2
    assert blocked == 3
