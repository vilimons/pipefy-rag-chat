from datetime import datetime
from typing import Any

from redis import Redis
from redis.commands.search.field import NumericField, TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from app.models.schemas import DocumentResponse, SourceChunk, parse_datetime
from app.services.embeddings import embedding_to_bytes
from app.services.ingestion import EmbeddedChunk

DOCUMENT_PREFIX = "document:"
CHUNK_PREFIX = "doc:"


class RedisDocumentRepository:
    def __init__(
        self,
        redis_client: Redis,
        index_name: str = "docs",
        vector_dim: int = 384,
    ) -> None:
        self.redis_client = redis_client
        self.index_name = index_name
        self.vector_dim = vector_dim

    def ensure_vector_index(self) -> None:
        try:
            self.redis_client.ft(self.index_name).info()
            return
        except ResponseError:
            pass

        schema = (
            TextField("file_id"),
            TextField("source"),
            NumericField("chunk_index"),
            TextField("content"),
            TextField("uploaded_at"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.vector_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        )

        definition = IndexDefinition(
            prefix=[CHUNK_PREFIX],
            index_type=IndexType.HASH,
        )

        self.redis_client.ft(self.index_name).create_index(
            fields=schema,
            definition=definition,
        )

    def save_document(
        self,
        file_id: str,
        filename: str,
        uploaded_at: datetime,
        chunks: list[EmbeddedChunk],
    ) -> None:
        self.ensure_vector_index()

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
                    "embedding": embedding_to_bytes(chunk.embedding),
                },
            )

    def list_documents(self) -> list[DocumentResponse]:
        documents: list[DocumentResponse] = []

        for key in self.redis_client.scan_iter(f"{DOCUMENT_PREFIX}*"):
            raw_document = self._decode_hash(self.redis_client.hgetall(key))

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
            documents,
            key=lambda document: document.uploaded_at,
            reverse=True,
        )

    def delete_document(self, file_id: str) -> bool:
        document_key = self._document_key(file_id)
        chunk_keys = list(self.redis_client.scan_iter(self._chunk_pattern(file_id)))

        keys_to_delete = [document_key, *chunk_keys]
        deleted_count = self.redis_client.delete(*keys_to_delete)

        return deleted_count > 0

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[SourceChunk]:
        self.ensure_vector_index()

        query = (
            Query(f"*=>[KNN {top_k} @embedding $query_vector AS score]")
            .sort_by("score")
            .return_fields(
                "file_id",
                "source",
                "chunk_index",
                "content",
                "score",
            )
            .dialect(2)
        )

        result = self.redis_client.ft(self.index_name).search(
            query,
            query_params={
                "query_vector": embedding_to_bytes(query_embedding),
            },
        )

        sources: list[SourceChunk] = []

        for document in result.docs:
            sources.append(
                SourceChunk(
                    chunk=str(document.content),
                    source=str(document.source),
                    score=float(document.score),
                    chunk_index=int(document.chunk_index),
                    file_id=str(document.file_id),
                )
            )

        return sources

    def _document_key(self, file_id: str) -> str:
        return f"{DOCUMENT_PREFIX}{file_id}"

    def _chunk_key(self, file_id: str, chunk_index: int) -> str:
        return f"{CHUNK_PREFIX}{file_id}:chunk:{chunk_index}"

    def _chunk_pattern(self, file_id: str) -> str:
        return f"{CHUNK_PREFIX}{file_id}:chunk:*"

    def _decode_hash(self, value: dict[Any, Any]) -> dict[str, str]:
        decoded: dict[str, str] = {}

        for key, item in value.items():
            decoded_key = key.decode("utf-8") if isinstance(key, bytes) else str(key)

            if isinstance(item, bytes):
                decoded[decoded_key] = item.decode("utf-8")
            else:
                decoded[decoded_key] = str(item)

        return decoded
