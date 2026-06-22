from datetime import UTC, datetime
from typing import Any

from redis.exceptions import ResponseError

from app.models.schemas import SourceChunk
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


def test_search_relevant_chunks_prioritizes_explicit_filename() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(
        redis_client=redis,  # type: ignore[arg-type]
        index_name="docs",
        vector_dim=384,
    )

    redis.hset(
        "document:file-pipefy",
        mapping={
            "file_id": "file-pipefy",
            "name": "teste.txt",
            "uploaded_at": "2026-06-21T18:57:39Z",
            "chunks": 1,
        },
    )
    redis.hset(
        "document:file-cabo-verde",
        mapping={
            "file_id": "file-cabo-verde",
            "name": "teste2.docx",
            "uploaded_at": "2026-06-21T18:57:44Z",
            "chunks": 1,
        },
    )
    redis.hset(
        "doc:file-pipefy:chunk:0",
        mapping={
            "file_id": "file-pipefy",
            "source": "teste.txt",
            "chunk_index": 0,
            "content": "Pipefy is a platform for workflow management.",
        },
    )
    redis.hset(
        "doc:file-cabo-verde:chunk:0",
        mapping={
            "file_id": "file-cabo-verde",
            "source": "teste2.docx",
            "chunk_index": 0,
            "content": "Cabo Verde é um país africano.",
        },
    )

    chunks = repository.search_relevant_chunks(
        question="O que você pode dizer sobre o teste.txt?",
        query_embedding=[0.1] * 384,
        top_k=3,
    )

    assert len(chunks) == 1
    assert chunks[0].source == "teste.txt"
    assert "Pipefy" in chunks[0].chunk


def test_select_diverse_chunks_prioritizes_distinct_documents() -> None:
    repository = RedisDocumentRepository(
        redis_client=FakeRedis(),  # type: ignore[arg-type]
        index_name="docs",
        vector_dim=384,
    )

    chunks = [
        SourceChunk(
            chunk="chunk a1",
            source="a.txt",
            score=0.1,
            chunk_index=0,
            file_id="doc-a",
        ),
        SourceChunk(
            chunk="chunk a2",
            source="a.txt",
            score=0.2,
            chunk_index=1,
            file_id="doc-a",
        ),
        SourceChunk(
            chunk="chunk b1",
            source="b.txt",
            score=0.3,
            chunk_index=0,
            file_id="doc-b",
        ),
        SourceChunk(
            chunk="chunk c1",
            source="c.txt",
            score=0.4,
            chunk_index=0,
            file_id="doc-c",
        ),
    ]

    selected = repository._select_diverse_chunks(
        chunks=chunks,
        top_k=3,
    )

    assert [chunk.file_id for chunk in selected] == [
        "doc-a",
        "doc-b",
        "doc-c",
    ]


def test_decode_hash_ignores_binary_embedding_field() -> None:
    repository = RedisDocumentRepository(
        redis_client=FakeRedis(),  # type: ignore[arg-type]
        index_name="docs",
        vector_dim=384,
    )

    decoded = repository._decode_hash(
        {
            b"file_id": b"file-1",
            b"source": b"document.txt",
            b"content": b"readable text",
            b"embedding": b"\xaf\x00\x00\x00",
        }
    )

    assert decoded == {
        "file_id": "file-1",
        "source": "document.txt",
        "content": "readable text",
    }
