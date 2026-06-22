from app.repositories.redis_repository import RedisDocumentRepository


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, dict[str, object]] = {}

    def hset(self, name: str, mapping: dict[str, object]) -> None:
        self.storage[name] = mapping

    def hgetall(self, name: str) -> dict[str, object]:
        return self.storage.get(name, {})

    def scan_iter(self, pattern: str):
        prefix = pattern.replace("*", "")

        for key in self.storage:
            if key.startswith(prefix):
                yield key


def create_document(
    redis: FakeRedis,
    file_id: str,
    filename: str,
    content: str,
) -> None:
    redis.hset(
        f"document:{file_id}",
        mapping={
            "file_id": file_id,
            "name": filename,
            "uploaded_at": "2026-06-21T18:57:39Z",
            "chunks": 1,
        },
    )
    redis.hset(
        f"doc:{file_id}:chunk:0",
        mapping={
            "file_id": file_id,
            "source": filename,
            "chunk_index": 0,
            "content": content,
        },
    )


def test_collection_overview_returns_chunks_from_multiple_documents() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(
        redis_client=redis,  # type: ignore[arg-type]
        index_name="docs",
        vector_dim=384,
    )

    create_document(
        redis=redis,
        file_id="doc-a",
        filename="documento-a.txt",
        content="Conteúdo representativo do primeiro documento.",
    )
    create_document(
        redis=redis,
        file_id="doc-b",
        filename="documento-b.pdf",
        content="Conteúdo representativo do segundo documento.",
    )
    create_document(
        redis=redis,
        file_id="doc-c",
        filename="documento-c.docx",
        content="Conteúdo representativo do terceiro documento.",
    )

    chunks = repository.search_relevant_chunks(
        question="Sobre o que tratam os documentos?",
        query_embedding=[0.1] * 384,
        top_k=3,
    )

    assert {chunk.source for chunk in chunks} == {
        "documento-a.txt",
        "documento-b.pdf",
        "documento-c.docx",
    }


def test_explicit_filename_returns_chunks_from_that_document() -> None:
    redis = FakeRedis()
    repository = RedisDocumentRepository(
        redis_client=redis,  # type: ignore[arg-type]
        index_name="docs",
        vector_dim=384,
    )

    create_document(
        redis=redis,
        file_id="doc-a",
        filename="relatorio-a.txt",
        content="Conteúdo do relatório A.",
    )
    create_document(
        redis=redis,
        file_id="doc-b",
        filename="relatorio-b.pdf",
        content="Conteúdo do relatório B.",
    )

    chunks = repository.search_relevant_chunks(
        question="Resuma o arquivo relatorio-a.txt",
        query_embedding=[0.1] * 384,
        top_k=3,
    )

    assert len(chunks) == 1
    assert chunks[0].source == "relatorio-a.txt"
    assert chunks[0].chunk == "Conteúdo do relatório A."
