from datetime import UTC, datetime

from app.repositories.redis_repository import RedisDocumentRepository
from app.services.chunking import TextChunk


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, dict[str, str]] = {}

    def hset(self, name: str, mapping: dict[str, object]) -> None:
        self.storage[name] = {key: str(value) for key, value in mapping.items()}

    def hgetall(self, name: str) -> dict[str, str]:
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
        TextChunk(content="first chunk", chunk_index=0),
        TextChunk(content="second chunk", chunk_index=1),
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


def test_repository_deletes_document_and_chunks() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(redis)  # type: ignore[arg-type]

    uploaded_at = datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    chunks = [TextChunk(content="first chunk", chunk_index=0)]

    repository.save_document(
        file_id="file-1",
        filename="example.txt",
        uploaded_at=uploaded_at,
        chunks=chunks,
    )

    deleted = repository.delete_document("file-1")

    assert deleted is True
    assert repository.list_documents() == []
