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
from app.rag.pipeline import build_fallback_answer, build_prompt
from app.repositories.redis_client import get_redis_client
from app.repositories.redis_repository import RedisDocumentRepository
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


def retrieve_sources(
    request: ChatRequest,
    settings: Settings,
    redis_client: Redis,
    embedding_service: EmbeddingService,
) -> list[SourceChunk]:
    query_embedding = embedding_service.embed_text(request.question)

    repository = RedisDocumentRepository(
        redis_client=redis_client,
        index_name=settings.redis_index_name,
        vector_dim=settings.redis_vector_dim,
    )

    return repository.search_similar_chunks(
        query_embedding=query_embedding,
        top_k=request.top_k,
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
    metadata = {
        "session_id": request.session_id,
        "top_k": request.top_k,
        "llm_provider": "ollama",
        "llm_model": settings.ollama_model,
        "embedding_model": settings.embedding_model_name,
        "environment": settings.app_env,
    }

    sources = tracer.trace(
        name="redis_vector_retrieval",
        run_type="retriever",
        inputs={
            "question": request.question,
            "top_k": request.top_k,
        },
        metadata=metadata,
        function=lambda: retrieve_sources(
            request=request,
            settings=settings,
            redis_client=redis_client,
            embedding_service=embedding_service,
        ),
    )

    history = history_service.get_messages(request.session_id)

    if not sources:
        answer = build_fallback_answer()
    else:
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

        try:
            answer = tracer.trace(
                name="ollama_generate",
                run_type="llm",
                inputs={
                    "prompt": prompt,
                    "model": settings.ollama_model,
                },
                metadata={
                    **metadata,
                    "source_count": len(sources),
                },
                function=lambda: ollama_client.generate(prompt),
            )
        except OllamaServiceError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    history_service.append_exchange(
        session_id=request.session_id,
        question=request.question,
        answer=answer,
    )

    return ChatResponse(
        answer=answer,
        sources=sources,
        session_id=request.session_id,
    )


@router.post("/retrieve", response_model=list[SourceChunk])
def retrieve_relevant_chunks(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
    embedding_service: EmbeddingService = Depends(get_chat_embedding_service),
) -> list[SourceChunk]:
    return retrieve_sources(
        request=request,
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
