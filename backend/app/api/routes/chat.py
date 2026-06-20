from fastapi import APIRouter, Depends
from redis import Redis

from app.core.config import Settings, get_settings
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk
from app.repositories.redis_client import get_redis_client
from app.repositories.redis_repository import RedisDocumentRepository
from app.services.embeddings import EmbeddingService, get_embedding_service

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_embedding_service(
    settings: Settings = Depends(get_settings),
) -> EmbeddingService:
    return get_embedding_service(settings.embedding_model_name)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        answer=(
            "RAG pipeline is not implemented yet. "
            "This placeholder confirms that the chat contract is working."
        ),
        sources=[],
        session_id=request.session_id,
    )


@router.post("/retrieve", response_model=list[SourceChunk])
def retrieve_relevant_chunks(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
    embedding_service: EmbeddingService = Depends(get_chat_embedding_service),
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
