from io import BytesIO

import pytest
from fastapi import UploadFile

from app.services.ingestion import ingest_uploaded_document


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
    )

    assert result.file_id
    assert result.filename == "example.txt"
    assert [chunk.content for chunk in result.chunks] == ["abcd", "defg", "ghij"]


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
    )

    assert len(result.file_id) == 36
