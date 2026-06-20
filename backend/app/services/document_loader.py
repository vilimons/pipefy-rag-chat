from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


class UnsupportedFileTypeError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_supported_file(filename: str) -> None:
    extension = get_file_extension(filename)

    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            "Unsupported file type. Only PDF and TXT files are allowed."
        )


async def extract_text_from_upload(file: UploadFile) -> str:
    filename = file.filename or ""
    validate_supported_file(filename)

    extension = get_file_extension(filename)
    content = await file.read()

    if extension == ".txt":
        text = _extract_text_from_txt(content)
    elif extension == ".pdf":
        text = _extract_text_from_pdf(content)
    else:
        raise UnsupportedFileTypeError(
            "Unsupported file type. Only PDF and TXT files are allowed."
        )

    normalized_text = normalize_text(text)

    if not normalized_text:
        raise EmptyDocumentError(
            "The uploaded document does not contain readable text."
        )

    return normalized_text


def _extract_text_from_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")


def _extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages_text: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages_text.append(page_text)

    return "\n\n".join(pages_text)


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines).strip()
