"""Retrieval utilities.

Fetches the top-k most relevant chunks from one or more indexed
collections for a given query, returning text plus source metadata.
"""

from dataclasses import dataclass, field

from app.core.dependencies import get_chroma_client, get_embed_model


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with its source attribution."""

    text: str
    score: float
    metadata: dict = field(default_factory=dict)

    @property
    def file_path(self) -> str:
        """Human-readable source label (file path / endpoint / repo)."""
        for key in ("file_path", "source", "title"):
            if self.metadata.get(key):
                return str(self.metadata[key])
        return "unknown source"


def retrieve(
    query: str, collection_names: list[str] | None = None, n_results: int = 10
) -> list[RetrievedChunk]:
    """Return the top-k chunks across the given collections.

    If `collection_names` is None, searches every collection (all indexed docs).
    """
    client = get_chroma_client()
    embed_model = get_embed_model()
    query_embedding = list(embed_model.get_query_embedding(query))

    # Decide which collections to search.
    all_collections = [c.name for c in client.list_collections()]
    targets = collection_names if collection_names else all_collections
    if not targets:
        return []

    results: list[RetrievedChunk] = []
    for name in targets:
        try:
            collection = client.get_collection(name)
        except ValueError:
            continue  # Collection was deleted mid-query — skip it.
        hit = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        documents = (hit.get("documents") or [[]])[0]
        metadatas = (hit.get("metadatas") or [[]])[0]
        distances = (hit.get("distances") or [[]])[0]
        for text, metadata, distance in zip(documents, metadatas, distances):
            # Chroma returns distances; convert to a similarity score in [0, 1].
            score = max(0.0, 1.0 - float(distance))
            results.append(
                RetrievedChunk(text=text, score=score, metadata=metadata or {})
            )

    # Sort by relevance, drop near-zero matches, cap at n_results.
    results.sort(key=lambda r: r.score, reverse=True)
    return [r for r in results if r.score > 0.1][:n_results]
