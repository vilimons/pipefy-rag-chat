from app.models.schemas import SourceChunk
from app.services.chat_history import ChatMessage


def build_fallback_answer() -> str:
    return (
        "I could not find relevant information in the indexed documents "
        "to answer this question."
    )


def format_history(messages: list[ChatMessage]) -> str:
    if not messages:
        return "No previous conversation."

    return "\n".join(f"{message.role}: {message.content}" for message in messages)


def build_prompt(
    question: str,
    sources: list[SourceChunk],
    history: list[ChatMessage] | None = None,
) -> str:
    context = "\n\n".join(
        (
            f"Source: {source.source}\n"
            f"Chunk index: {source.chunk_index}\n"
            f"Content: {source.chunk}"
        )
        for source in sources
    )

    conversation_history = format_history(history or [])

    return f"""You are a RAG assistant for a technical document search system.

Answer the user's question using only the context below.
If the context does not contain enough information, say that you do not know
based on the indexed documents.
Do not use external knowledge.
Be concise and direct.

Conversation history:
{conversation_history}

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
