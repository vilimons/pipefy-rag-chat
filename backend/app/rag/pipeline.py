from app.models.schemas import SourceChunk


def build_answer_from_sources(question: str, sources: list[SourceChunk]) -> str:
    if not sources:
        return (
            "I could not find relevant information in the indexed documents "
            "to answer this question."
        )

    context_lines = [f"- {source.chunk}" for source in sources]

    context = "\n".join(context_lines)

    return (
        "Based on the indexed documents, here is the most relevant context "
        f"for your question: {question}\n\n"
        f"{context}"
    )
