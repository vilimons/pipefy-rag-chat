from datetime import datetime

from redis import Redis

from app.models.schemas import DocumentResponse, parse_datetime
from app.services.chunking import TextChunk

DOCUMENT_PREFIX = "document:"
CHUNK_PREFIX = "doc:"


class RedisDocumentRepository:
    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    def save_document(
        self,
        file_id: str,
        filename: str,
        uploaded_at: datetime,
        chunks: list[TextChunk],
    ) -> None:
        document_key = self._document_key(file_id)

        self.redis_client.hset(
            document_key,
            mapping={
                "file_id": file_id,
                "name": filename,
                "uploaded_at": uploaded_at.isoformat(),
                "chunks": len(chunks),
            },
        )

        for chunk in chunks:
            chunk_key = self._chunk_key(file_id, chunk.chunk_index)
            self.redis_client.hset(
                chunk_key,
                mapping={
                    "file_id": file_id,
                    "source": filename,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "uploaded_at": uploaded_at.isoformat(),
                },
            )

    def list_documents(self) -> list[DocumentResponse]:
        documents: list[DocumentResponse] = []

        for key in self.redis_client.scan_iter(f"{DOCUMENT_PREFIX}*"):
            raw_document = self.redis_client.hgetall(key)

            if not raw_document:
                continue

            documents.append(
                DocumentResponse(
                    file_id=raw_document["file_id"],
                    name=raw_document["name"],
                    uploaded_at=parse_datetime(raw_document["uploaded_at"]),
                    chunks=int(raw_document["chunks"]),
                )
            )

        return sorted(
            documents, key=lambda document: document.uploaded_at, reverse=True
        )

    def delete_document(self, file_id: str) -> bool:
        document_key = self._document_key(file_id)
        chunk_keys = list(self.redis_client.scan_iter(self._chunk_pattern(file_id)))

        keys_to_delete = [document_key, *chunk_keys]

        deleted_count = self.redis_client.delete(*keys_to_delete)

        return deleted_count > 0

    def _document_key(self, file_id: str) -> str:
        return f"{DOCUMENT_PREFIX}{file_id}"

    def _chunk_key(self, file_id: str, chunk_index: int) -> str:
        return f"{CHUNK_PREFIX}{file_id}:chunk:{chunk_index}"

    def _chunk_pattern(self, file_id: str) -> str:
        return f"{CHUNK_PREFIX}{file_id}:chunk:*"
