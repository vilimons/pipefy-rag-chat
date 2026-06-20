from datetime import UTC, datetime
from typing import Any

from redis.exceptions import ResponseError

from app.repositories.redis_repository import RedisDocumentRepository
from app.services.ingestion import EmbeddedChunk


class FakeSearchIndex:
    def info(self) -> dict[str, str]:
        raise ResponseError("unknown index name")

    def create_index(self, fields: object, definition: object) -> None:
        return None

    def search(self, query: object, query_params: dict[str, bytes]):
        class Result:
            docs: list[object] = []

        return Result()


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, dict[str, Any]] = {}
        self.index = FakeSearchIndex()

    def ft(self, index_name: str) -> FakeSearchIndex:
        return self.index

    def hset(self, name: str, mapping: dict[str, object]) -> None:
        self.storage[name] = dict(mapping)

    def hgetall(self, name: str) -> dict[str, Any]:
        return self.storage.get(name, {})

    def scan_iter(self, pattern: str):
        prefix = pattern.replace("*", "")
        for key in list(self.storage):
            if key.startswith(prefix):
                yield key

    def delete(self, *names: str) -> int:
        deleted_count = 0
        for name in names:
            if name in self.storage:
                del self.storage[name]
                deleted_count += 1
        return deleted_count


def test_repository_saves_and_lists_documents() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(redis)  # type: ignore[arg-type]

    uploaded_at = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    chunks = [
        EmbeddedChunk(content="first chunk", chunk_index=0, embedding=[0.1] * 384),
        EmbeddedChunk(content="second chunk", chunk_index=1, embedding=[0.2] * 384),
    ]

    repository.save_document(
        file_id="file-1",
        filename="example.txt",
        uploaded_at=uploaded_at,
        chunks=chunks,
    )

    documents = repository.list_documents()

    assert len(documents) == 1
    assert documents[0].file_id == "file-1"
    assert documents[0].name == "example.txt"
    assert documents[0].chunks == 2


def test_repository_saves_embedding_as_bytes() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(redis)  # type: ignore[arg-type]

    uploaded_at = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    chunks = [
        EmbeddedChunk(content="first chunk", chunk_index=0, embedding=[0.1] * 384)
    ]

    repository.save_document(
        file_id="file-1",
        filename="example.txt",
        uploaded_at=uploaded_at,
        chunks=chunks,
    )

    chunk = redis.storage["doc:file-1:chunk:0"]

    assert isinstance(chunk["embedding"], bytes)
    assert len(chunk["embedding"]) == 384 * 4


def test_repository_deletes_document_and_chunks() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(redis)  # type: ignore[arg-type]

    uploaded_at = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    chunks = [
        EmbeddedChunk(content="first chunk", chunk_index=0, embedding=[0.1] * 384)
    ]

    repository.save_document(
        file_id="file-1",
        filename="example.txt",
        uploaded_at=uploaded_at,
        chunks=chunks,
    )

    deleted = repository.delete_document("file-1")

    assert deleted is True
    assert repository.list_documents() == []


def test_repository_search_similar_chunks_returns_empty_list_when_no_docs() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(redis)  # type: ignore[arg-type]

    result = repository.search_similar_chunks(
        query_embedding=[0.1] * 384,
        top_k=5,
    )

    assert result == []
