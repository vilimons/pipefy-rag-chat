from fastapi import APIRouter, Depends
from redis import Redis

from app.models.schemas import DeleteDocumentResponse, DocumentResponse
from app.repositories.redis_client import get_redis_client
from app.repositories.redis_repository import RedisDocumentRepository

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    redis_client: Redis = Depends(get_redis_client),
) -> list[DocumentResponse]:
    repository = RedisDocumentRepository(redis_client)
    return repository.list_documents()


@router.delete("/{file_id}", response_model=DeleteDocumentResponse)
def delete_document(
    file_id: str,
    redis_client: Redis = Depends(get_redis_client),
) -> DeleteDocumentResponse:
    repository = RedisDocumentRepository(redis_client)
    deleted = repository.delete_document(file_id)

    return DeleteDocumentResponse(deleted=deleted, file_id=file_id)
