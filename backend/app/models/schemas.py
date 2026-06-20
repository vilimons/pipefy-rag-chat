from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    redis: str


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    chunks_indexed: int
    status: str


class DocumentResponse(BaseModel):
    file_id: str
    name: str
    uploaded_at: datetime
    chunks: int


class DeleteDocumentResponse(BaseModel):
    deleted: bool
    file_id: str


class SourceChunk(BaseModel):
    chunk: str
    source: str
    score: float
    chunk_index: int | None = None
    file_id: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    top_k: int = Field(default=5, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    session_id: str


class ChatMessageResponse(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageResponse]


class ClearChatHistoryResponse(BaseModel):
    session_id: str
    deleted: bool


class ErrorResponse(BaseModel):
    detail: str | list[dict[str, Any]]


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
