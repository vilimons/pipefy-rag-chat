from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.models.schemas import UploadResponse
from app.services.document_loader import EmptyDocumentError, UnsupportedFileTypeError
from app.services.ingestion import ingest_uploaded_document

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    try:
        ingested_document = await ingest_uploaded_document(
            file=file,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
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

    return UploadResponse(
        file_id=ingested_document.file_id,
        filename=ingested_document.filename,
        chunks_indexed=len(ingested_document.chunks),
        status="processed",
    )
