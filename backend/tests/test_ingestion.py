from io import BytesIO

import pytest
from fastapi import UploadFile

from app.services.ingestion import ingest_uploaded_document


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]


@pytest.mark.asyncio
async def test_ingest_uploaded_txt_document_returns_chunks() -> None:
    file = UploadFile(
        filename="example.txt",
        file=BytesIO(b"abcdefghij"),
    )

    result = await ingest_uploaded_document(
        file=file,
        chunk_size=4,
        chunk_overlap=1,
        embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
    )

    assert result.file_id
    assert result.filename == "example.txt"
    assert [chunk.content for chunk in result.chunks] == ["abcd", "defg", "ghij"]
    assert all(len(chunk.embedding) == 384 for chunk in result.chunks)


@pytest.mark.asyncio
async def test_ingest_uploaded_txt_document_returns_uuid_like_file_id() -> None:
    file = UploadFile(
        filename="example.txt",
        file=BytesIO(b"hello world"),
    )

    result = await ingest_uploaded_document(
        file=file,
        chunk_size=100,
        chunk_overlap=10,
        embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
    )

    assert len(result.file_id) == 36
