"""Prompt templates for the documentation assistant.

The system prompt defines the assistant persona and grounding rules.
The RAG prompt wraps retrieved context so the LLM answers strictly from
the provided documentation chunks.
"""

# System prompt set once per conversation.
SYSTEM_PROMPT = """You are a developer documentation assistant.
You answer questions about the user's indexed documentation — GitHub
repositories, API specs, PDFs, and README files.

Rules:
- Answer using ONLY the provided context chunks below. If the answer is
  not in the context, say you don't know rather than guessing.
- When you use information from a source, cite it inline as [1], [2], etc.
  matching the order sources are listed in the context.
- Be concise and technical. Use markdown for structure when helpful.
- Include code snippets or API details exactly as they appear in the docs."""

# RAG context template: joins retrieved chunks with numbered citations.
RAG_CONTEXT_TEMPLATE = """Context from the indexed documentation:

{context}

---

User question: {question}

Answer the question using the context above. Cite sources as [1], [2], ..."""


def build_context_text(chunks: list[str]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt."""
    numbered = [f"[{i + 1}] {chunk}" for i, chunk in enumerate(chunks)]
    return "\n\n".join(numbered)


def build_rag_prompt(question: str, chunks: list[str]) -> str:
    """Assemble the full user message for a RAG query."""
    return RAG_CONTEXT_TEMPLATE.format(
        context=build_context_text(chunks), question=question
    )
