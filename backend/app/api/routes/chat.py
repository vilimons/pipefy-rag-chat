from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis

from app.core.config import Settings, get_settings
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk
from app.rag.pipeline import build_fallback_answer, build_prompt
from app.repositories.redis_client import get_redis_client
from app.repositories.redis_repository import RedisDocumentRepository
from app.services.chat_history import ChatHistoryService
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.ollama import OllamaClient, OllamaServiceError

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
) -> ChatResponse:
    sources = retrieve_sources(
        request=request,
        settings=settings,
        redis_client=redis_client,
        embedding_service=embedding_service,
    )

    history = history_service.get_messages(request.session_id)

    if not sources:
        answer = build_fallback_answer()
    else:
        prompt = build_prompt(
            question=request.question,
            sources=sources,
            history=history,
        )

        try:
            answer = ollama_client.generate(prompt)
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
