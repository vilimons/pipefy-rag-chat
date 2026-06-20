import pytest
from fastapi import UploadFile

from app.services.document_loader import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
    extract_text_from_upload,
    get_file_extension,
    normalize_text,
    validate_supported_file,
)


def test_get_file_extension_returns_lowercase_extension() -> None:
    assert get_file_extension("Report.PDF") == ".pdf"
    assert get_file_extension("notes.TXT") == ".txt"


def test_validate_supported_file_accepts_pdf_and_txt() -> None:
    validate_supported_file("example.pdf")
    validate_supported_file("example.txt")


def test_validate_supported_file_rejects_other_extensions() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_supported_file("example.docx")


def test_normalize_text_removes_empty_lines_and_extra_spaces() -> None:
    text = "  hello  \n\n  world  \n"
    assert normalize_text(text) == "hello\nworld"


@pytest.mark.asyncio
async def test_extract_text_from_txt_upload() -> None:
    file = UploadFile(
        filename="example.txt",
        file=__import__("io").BytesIO(b" hello world \n\n from txt "),
    )

    text = await extract_text_from_upload(file)

    assert text == "hello world\nfrom txt"


@pytest.mark.asyncio
async def test_extract_text_from_empty_txt_raises_error() -> None:
    file = UploadFile(
        filename="empty.txt",
        file=__import__("io").BytesIO(b"   \n\n   "),
    )

    with pytest.raises(EmptyDocumentError):
        await extract_text_from_upload(file)
