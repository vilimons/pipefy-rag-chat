from dataclasses import dataclass
from uuid import uuid4

from fastapi import UploadFile

from app.services.chunking import TextChunk, split_text_into_chunks
from app.services.document_loader import extract_text_from_upload


@dataclass(frozen=True)
class IngestedDocument:
    file_id: str
    filename: str
    chunks: list[TextChunk]


async def ingest_uploaded_document(
    file: UploadFile,
    chunk_size: int,
    chunk_overlap: int,
) -> IngestedDocument:
    text = await extract_text_from_upload(file)
    chunks = split_text_into_chunks(
        text=text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return IngestedDocument(
        file_id=str(uuid4()),
        filename=file.filename or "unknown",
        chunks=chunks,
    )
