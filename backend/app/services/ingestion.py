from dataclasses import dataclass
from uuid import uuid4

from fastapi import UploadFile

from app.services.chunking import split_text_into_chunks
from app.services.document_loader import extract_text_from_upload
from app.services.embeddings import EmbeddingService


@dataclass(frozen=True)
class EmbeddedChunk:
    content: str
    chunk_index: int
    embedding: list[float]


@dataclass(frozen=True)
class IngestedDocument:
    file_id: str
    filename: str
    chunks: list[EmbeddedChunk]


async def ingest_uploaded_document(
    file: UploadFile,
    chunk_size: int,
    chunk_overlap: int,
    embedding_service: EmbeddingService,
) -> IngestedDocument:
    text = await extract_text_from_upload(file)
    text_chunks = split_text_into_chunks(
        text=text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    embeddings = embedding_service.embed_texts([chunk.content for chunk in text_chunks])

    chunks = [
        EmbeddedChunk(
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            embedding=embedding,
        )
        for chunk, embedding in zip(text_chunks, embeddings, strict=True)
    ]

    return IngestedDocument(
        file_id=str(uuid4()),
        filename=file.filename or "unknown",
        chunks=chunks,
    )
