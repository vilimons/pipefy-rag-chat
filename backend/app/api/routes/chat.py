from fastapi import APIRouter, Depends, HTTPException, status
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
