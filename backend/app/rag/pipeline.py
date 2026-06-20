from app.models.schemas import SourceChunk


def build_fallback_answer() -> str:
    return (
        "I could not find relevant information in the indexed documents "
        "to answer this question."
    )


def build_prompt(question: str, sources: list[SourceChunk]) -> str:
    context = "\n\n".join(
        (
            f"Source: {source.source}\n"
            f"Chunk index: {source.chunk_index}\n"
            f"Content: {source.chunk}"
        )
        for source in sources
    )

    return f"""You are a RAG assistant for a technical document search system.

Answer the user's question using only the context below.
If the context does not contain enough information, say that you do not know
based on the indexed documents.
Do not use external knowledge.
Be concise and direct.

Question:
{question}

Context:
{context}

Answer:
"""


def build_answer_from_sources(question: str, sources: list[SourceChunk]) -> str:
    if not sources:
        return build_fallback_answer()

    context_lines = [f"- {source.chunk}" for source in sources]
    context = "\n".join(context_lines)

    return (
        "Based on the indexed documents, here is the most relevant context "
        f"for your question: {question}\n\n"
        f"{context}"
    )
