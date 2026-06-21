import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from redis import Redis

from app.core.config import Settings, get_settings
from app.models.schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ClearChatHistoryResponse,
    SourceChunk,
)
from app.rag.graph import retrieve_sources, run_rag_graph
from app.rag.pipeline import build_fallback_answer, build_prompt
from app.repositories.redis_client import get_redis_client
from app.services.chat_history import ChatHistoryService
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.ollama import OllamaClient, OllamaServiceError
from app.services.tracing import LangSmithTracer, get_langsmith_tracer

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_embedding_service(
    settings: Settings = Depends(get_settings),
) -> EmbeddingService:
    return get_embedding_service(settings.embedding_model_name)


def get_ollama_client(
    settings: Settings = Depends(get_settings),
) -> OllamaClient:
    return OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )


def get_chat_history_service(
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
) -> ChatHistoryService:
    return ChatHistoryService(
        redis_client=redis_client,
        max_messages=settings.max_history_messages,
    )


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
    embedding_service: EmbeddingService = Depends(get_chat_embedding_service),
    ollama_client: OllamaClient = Depends(get_ollama_client),
    history_service: ChatHistoryService = Depends(get_chat_history_service),
    tracer: LangSmithTracer = Depends(get_langsmith_tracer),
) -> ChatResponse:
    try:
        return run_rag_graph(
            question=request.question,
            session_id=request.session_id,
            top_k=request.top_k,
            settings=settings,
            redis_client=redis_client,
            embedding_service=embedding_service,
            ollama_client=ollama_client,
            history_service=history_service,
            tracer=tracer,
        )
    except OllamaServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.post("/stream")
def stream_chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
    embedding_service: EmbeddingService = Depends(get_chat_embedding_service),
    ollama_client: OllamaClient = Depends(get_ollama_client),
    history_service: ChatHistoryService = Depends(get_chat_history_service),
    tracer: LangSmithTracer = Depends(get_langsmith_tracer),
) -> StreamingResponse:
    return StreamingResponse(
        _stream_chat_events(
            request=request,
            settings=settings,
            redis_client=redis_client,
            embedding_service=embedding_service,
            ollama_client=ollama_client,
            history_service=history_service,
            tracer=tracer,
        ),
        media_type="text/event-stream",
    )


def _stream_chat_events(
    request: ChatRequest,
    settings: Settings,
    redis_client: Redis,
    embedding_service: EmbeddingService,
    ollama_client: OllamaClient,
    history_service: ChatHistoryService,
    tracer: LangSmithTracer,
) -> Iterator[str]:
    metadata = {
        "session_id": request.session_id,
        "top_k": request.top_k,
        "llm_provider": "ollama",
        "llm_model": settings.ollama_model,
        "embedding_model": settings.embedding_model_name,
        "environment": settings.app_env,
        "streaming": True,
        "orchestrator": "sse_stream",
    }

    yield _sse_event(
        "metadata",
        {
            "session_id": request.session_id,
            "model": settings.ollama_model,
        },
    )

    sources = tracer.trace(
        name="redis_vector_retrieval",
        run_type="retriever",
        inputs={
            "question": request.question,
            "top_k": request.top_k,
        },
        metadata=metadata,
        function=lambda: retrieve_sources(
            question=request.question,
            top_k=request.top_k,
            settings=settings,
            redis_client=redis_client,
            embedding_service=embedding_service,
        ),
    )

    yield _sse_event(
        "sources",
        [source.model_dump() for source in sources],
    )

    history = history_service.get_messages(request.session_id)

    if not sources:
        answer = build_fallback_answer()

        yield _sse_event("token", answer)

        history_service.append_exchange(
            session_id=request.session_id,
            question=request.question,
            answer=answer,
        )

        yield _sse_event(
            "done",
            {
                "answer": answer,
                "session_id": request.session_id,
            },
        )
        return

    prompt = tracer.trace(
        name="build_rag_prompt",
        run_type="chain",
        inputs={
            "question": request.question,
            "source_count": len(sources),
            "history_count": len(history),
        },
        metadata=metadata,
        function=lambda: build_prompt(
            question=request.question,
            sources=sources,
            history=history,
        ),
    )

    answer_parts: list[str] = []

    try:
        for token in ollama_client.stream_generate(prompt):
            answer_parts.append(token)
            yield _sse_event("token", token)
    except OllamaServiceError as error:
        yield _sse_event("error", str(error))
        return

    answer = "".join(answer_parts).strip()

    history_service.append_exchange(
        session_id=request.session_id,
        question=request.question,
        answer=answer,
    )

    yield _sse_event(
        "done",
        {
            "answer": answer,
            "session_id": request.session_id,
        },
    )


def _sse_event(event: str, data: Any) -> str:
    return f"event: {event}\n" f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/retrieve", response_model=list[SourceChunk])
def retrieve_relevant_chunks(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
    embedding_service: EmbeddingService = Depends(get_chat_embedding_service),
) -> list[SourceChunk]:
    return retrieve_sources(
        question=request.question,
        top_k=request.top_k,
        settings=settings,
        redis_client=redis_client,
        embedding_service=embedding_service,
    )


@router.get(
    "/sessions/{session_id}/history",
    response_model=ChatHistoryResponse,
)
def get_chat_history(
    session_id: str,
    history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatHistoryResponse:
    messages = history_service.get_messages(session_id)

    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            ChatMessageResponse(
                role=message.role,
                content=message.content,
            )
            for message in messages
        ],
    )


@router.delete(
    "/sessions/{session_id}/history",
    response_model=ClearChatHistoryResponse,
)
def clear_chat_history(
    session_id: str,
    history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> ClearChatHistoryResponse:
    deleted = history_service.clear_history(session_id)

    return ClearChatHistoryResponse(
        session_id=session_id,
        deleted=deleted,
    )
