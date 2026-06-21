from io import BytesIO

import pytest
from docx import Document as DocxDocument
from fastapi import UploadFile

from app.services.document_loader import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
    extract_text_from_upload,
    normalize_text,
)


def test_normalize_text_removes_blank_lines_and_extra_spaces() -> None:
    text = " first line \n\n second line \n "

    assert normalize_text(text) == "first line\nsecond line"


@pytest.mark.asyncio
async def test_extract_text_from_txt_upload() -> None:
    file = UploadFile(
        filename="example.txt",
        file=BytesIO(b"hello world"),
    )

    text = await extract_text_from_upload(file)

    assert text == "hello world"


@pytest.mark.asyncio
async def test_extract_text_from_docx_upload() -> None:
    buffer = BytesIO()
    document = DocxDocument()
    document.add_paragraph("Pipefy is a workflow management platform.")
    document.save(buffer)
    buffer.seek(0)

    file = UploadFile(
        filename="example.docx",
        file=BytesIO(buffer.read()),
    )

    text = await extract_text_from_upload(file)

    assert text == "Pipefy is a workflow management platform."


@pytest.mark.asyncio
async def test_extract_text_from_upload_rejects_unsupported_extension() -> None:
    file = UploadFile(
        filename="example.csv",
        file=BytesIO(b"hello world"),
    )

    with pytest.raises(UnsupportedFileTypeError):
        await extract_text_from_upload(file)


@pytest.mark.asyncio
async def test_extract_text_from_upload_rejects_empty_txt() -> None:
    file = UploadFile(
        filename="empty.txt",
        file=BytesIO(b"   \n\n"),
    )

    with pytest.raises(EmptyDocumentError):
        await extract_text_from_upload(file)
