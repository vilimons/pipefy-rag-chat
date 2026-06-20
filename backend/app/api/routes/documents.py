from fastapi import APIRouter

from app.models.schemas import DeleteDocumentResponse, DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents() -> list[DocumentResponse]:
    # Temporary placeholder. Redis-backed listing will be implemented next.
    return []


@router.delete("/{file_id}", response_model=DeleteDocumentResponse)
def delete_document(file_id: str) -> DeleteDocumentResponse:
    # Temporary placeholder. Redis-backed deletion will be implemented next.
    return DeleteDocumentResponse(deleted=False, file_id=file_id)
