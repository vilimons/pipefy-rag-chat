from collections.abc import Callable, Generator
from typing import Any, TypeVar

import pytest
from fastapi.testclient import TestClient

from app.api.routes.chat import (
    get_chat_embedding_service,
    get_chat_history_service,
    get_langsmith_tracer,
    get_ollama_client,
)
from app.api.routes.upload import get_upload_embedding_service
from app.main import app
from app.repositories.redis_client import get_redis_client
from app.services.chat_history import ChatHistoryService

T = TypeVar("T")


class FakeEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        return [0.1] * 384

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]


class FakeOllamaClient:
    def generate(self, prompt: str) -> str:
        return "Fake LLM answer based on retrieved context."


class FakeTracer:
    def trace(
        self,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any],
        function: Callable[[], T],
    ) -> T:
        return function()


class FakeSearchResult:
    docs: list[object] = []


class FakeSearchIndex:
    def info(self) -> dict[str, str]:
        return {"index": "docs"}

    def create_index(self, fields: object, definition: object) -> None:
        return None

    def search(
        self,
        query: object,
        query_params: dict[str, bytes],
    ) -> FakeSearchResult:
        return FakeSearchResult()


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, Any] = {}
        self.index = FakeSearchIndex()

    def ft(self, index_name: str) -> FakeSearchIndex:
        return self.index

    def hset(self, name: str, mapping: dict[str, object]) -> None:
        self.storage[name] = dict(mapping)

    def hgetall(self, name: str) -> dict[str, Any]:
        value = self.storage.get(name, {})

        if isinstance(value, dict):
            return value

        return {}

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

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        values = self.storage.get(name, [])

        if not isinstance(values, list):
            return []

        if end == -1:
            return values[start:]

        return values[start : end + 1]

    def rpush(self, name: str, value: str) -> None:
        self.storage.setdefault(name, []).append(value)

    def ltrim(self, name: str, start: int, end: int) -> None:
        values = self.storage.get(name, [])

        if not isinstance(values, list):
            return

        if start < 0:
            start = max(len(values) + start, 0)

        if end < 0:
            end = len(values) + end

        self.storage[name] = values[start : end + 1]


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def fake_history_service(fake_redis: FakeRedis) -> ChatHistoryService:
    return ChatHistoryService(
        redis_client=fake_redis,  # type: ignore[arg-type]
        max_messages=6,
    )


@pytest.fixture(autouse=True)
def override_services(
    fake_redis: FakeRedis,
    fake_history_service: ChatHistoryService,
) -> Generator[None, None, None]:
    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    app.dependency_overrides[get_upload_embedding_service] = (
        lambda: FakeEmbeddingService()
    )
    app.dependency_overrides[get_chat_embedding_service] = (
        lambda: FakeEmbeddingService()
    )
    app.dependency_overrides[get_ollama_client] = lambda: FakeOllamaClient()
    app.dependency_overrides[get_chat_history_service] = lambda: fake_history_service
    app.dependency_overrides[get_langsmith_tracer] = lambda: FakeTracer()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
