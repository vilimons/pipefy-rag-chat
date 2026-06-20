from fastapi import APIRouter, Depends
from redis import Redis

from app.core.config import Settings, get_settings
from app.models.schemas import DeleteDocumentResponse, DocumentResponse
from app.repositories.redis_client import get_redis_client
from app.repositories.redis_repository import RedisDocumentRepository

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_repository(
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
) -> RedisDocumentRepository:
    return RedisDocumentRepository(
        redis_client=redis_client,
        index_name=settings.redis_index_name,
        vector_dim=settings.redis_vector_dim,
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    repository: RedisDocumentRepository = Depends(get_document_repository),
) -> list[DocumentResponse]:
    return repository.list_documents()


@router.delete("/{file_id}", response_model=DeleteDocumentResponse)
def delete_document(
    file_id: str,
    repository: RedisDocumentRepository = Depends(get_document_repository),
) -> DeleteDocumentResponse:
    deleted = repository.delete_document(file_id)

    return DeleteDocumentResponse(deleted=deleted, file_id=file_id)
