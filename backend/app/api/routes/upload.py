from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.schemas import UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def _get_file_extension(filename: str) -> str:
    dot_index = filename.rfind(".")
    if dot_index == -1:
        return ""
    return filename[dot_index:].lower()


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    extension = _get_file_extension(file.filename or "")

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only PDF and TXT files are allowed.",
        )

    # Temporary placeholder. Real ingestion will be implemented next.
    return UploadResponse(
        file_id="placeholder-file-id",
        filename=file.filename or "unknown",
        chunks_indexed=0,
        status="accepted",
    )
