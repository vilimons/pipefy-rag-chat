from app.models.schemas import SourceChunk
from app.services.chat_history import ChatMessage


def build_fallback_answer() -> str:
    return (
        "Não encontrei informações relevantes nos documentos indexados "
        "para responder a essa pergunta."
    )


def format_history(messages: list[ChatMessage]) -> str:
    if not messages:
        return "Nenhuma conversa anterior."

    return "\n".join(f"{message.role}: {message.content}" for message in messages)


def build_prompt(
    question: str,
    sources: list[SourceChunk],
    history: list[ChatMessage] | None = None,
) -> str:
    context = "\n\n".join(
        (
            f"Fonte: {source.source}\n"
            f"Índice do chunk: {source.chunk_index}\n"
            f"Conteúdo: {source.chunk}"
        )
        for source in sources
    )

    conversation_history = format_history(history or [])

    return f"""Você é um assistente RAG para consulta técnica de documentos.

Responda à pergunta do usuário usando somente o contexto abaixo.
Se o contexto não tiver informação suficiente, diga que não sabe com base
nos documentos indexados.
Não use conhecimento externo.
Responda em português brasileiro, a menos que o usuário peça explicitamente
outro idioma.
Seja direto e objetivo.

Histórico da conversa:
{conversation_history}

Pergunta:
{question}

Contexto:
{context}

Resposta:
"""


def build_answer_from_sources(question: str, sources: list[SourceChunk]) -> str:
    if not sources:
        return build_fallback_answer()

    context_lines = [f"- {source.chunk}" for source in sources]
    context = "\n".join(context_lines)

    return (
        "Com base nos documentos indexados, este é o contexto mais relevante "
        f"para a sua pergunta: {question}\n\n"
        f"{context}"
    )
