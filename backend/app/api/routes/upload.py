from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from redis import Redis

from app.core.config import Settings, get_settings
from app.models.schemas import UploadResponse, utc_now
from app.repositories.redis_client import get_redis_client
from app.repositories.redis_repository import RedisDocumentRepository
from app.services.document_loader import EmptyDocumentError, UnsupportedFileTypeError
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.ingestion import ingest_uploaded_document

router = APIRouter(prefix="/upload", tags=["upload"])


def get_upload_embedding_service(
    settings: Settings = Depends(get_settings),
) -> EmbeddingService:
    return get_embedding_service(settings.embedding_model_name)


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    redis_client: Redis = Depends(get_redis_client),
    embedding_service: EmbeddingService = Depends(get_upload_embedding_service),
) -> UploadResponse:
    try:
        ingested_document = await ingest_uploaded_document(
            file=file,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            embedding_service=embedding_service,
        )
    except UnsupportedFileTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except EmptyDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    repository = RedisDocumentRepository(
        redis_client=redis_client,
        index_name=settings.redis_index_name,
        vector_dim=settings.redis_vector_dim,
    )
    repository.save_document(
        file_id=ingested_document.file_id,
        filename=ingested_document.filename,
        uploaded_at=utc_now(),
        chunks=ingested_document.chunks,
    )

    return UploadResponse(
        file_id=ingested_document.file_id,
        filename=ingested_document.filename,
        chunks_indexed=len(ingested_document.chunks),
        status="indexed",
    )
