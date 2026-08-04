"""End-to-end API smoke test (offline).

Exercises the full HTTP surface — health, upload, search, chat, documents,
delete — using a deterministic fake embedding model so no external provider
is required. Run with: python -m tests.e2e_smoke
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.core import dependencies  # noqa: E402
from app.main import app  # noqa: E402
from tests.conftest import FakeEmbedModel  # noqa: E402

# Inject the fake embedding model for the whole run.
dependencies._embed_model = FakeEmbedModel()

client = TestClient(app)

print("== health ==")
r = client.get("/health")
assert r.status_code == 200, r.text
print("OK:", r.json())

print("== upload markdown ==")
r = client.post(
    "/api/v1/documents/upload",
    files={"files": ("kafka.md", b"# Kafka\n\nKafka retry is configured via the retries property.", "text/markdown")},
)
assert r.status_code == 200, r.text
upload_doc = r.json()
print("OK:", upload_doc)

print("== list documents ==")
r = client.get("/api/v1/documents")
assert r.status_code == 200 and r.json()["documents"]
print("OK:", r.json()["documents"])

print("== search ==")
r = client.post("/api/v1/search", json={"query": "how is kafka retry configured", "n_results": 5})
assert r.status_code == 200, r.text
results = r.json()["results"]
assert results, "no results returned"
print("OK:", results[0]["file_path"], "score=", results[0]["score"])

print("== chat (no LLM key -> 503, graceful) ==")
r = client.post("/api/v1/chat", json={"query": "what is kafka retry?"})
print("status:", r.status_code)
if r.status_code == 503:
    print("OK (expected offline):", r.json()["detail"][:80])
else:
    assert r.status_code == 200, r.text

print("== delete document ==")
r = client.delete(f"/api/v1/documents/{upload_doc['id']}")
assert r.status_code == 200, r.text
print("OK:", r.json())

print("== list after delete ==")
r = client.get("/api/v1/documents")
assert r.status_code == 200 and not r.json()["documents"]
print("OK: empty")

print("\nALL E2E SMOKE TESTS PASSED")
