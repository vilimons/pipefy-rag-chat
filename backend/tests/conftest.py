from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.api.routes.chat import (
    get_chat_embedding_service,
    get_chat_history_service,
    get_ollama_client,
)
from app.api.routes.upload import get_upload_embedding_service
from app.main import app
from app.services.chat_history import ChatHistoryService


class FakeEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        return [0.1] * 384

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]


class FakeOllamaClient:
    def generate(self, prompt: str) -> str:
        return "Fake LLM answer based on retrieved context."


class FakeRedisForHistory:
    def __init__(self) -> None:
        self.storage: dict[str, list[str]] = {}

    def lrange(self, name: str, start: int, end: int) -> list[str]:
        values = self.storage.get(name, [])

        if end == -1:
            return values[start:]

        return values[start : end + 1]

    def rpush(self, name: str, value: str) -> None:
        self.storage.setdefault(name, []).append(value)

    def ltrim(self, name: str, start: int, end: int) -> None:
        values = self.storage.get(name, [])

        if start < 0:
            start = max(len(values) + start, 0)

        if end < 0:
            end = len(values) + end

        self.storage[name] = values[start : end + 1]

    def delete(self, name: str) -> int:
        if name not in self.storage:
            return 0

        del self.storage[name]
        return 1


@pytest.fixture
def fake_history_service() -> ChatHistoryService:
    return ChatHistoryService(
        redis_client=FakeRedisForHistory(),  # type: ignore[arg-type]
        max_messages=6,
    )


@pytest.fixture(autouse=True)
def override_ai_services(
    fake_history_service: ChatHistoryService,
) -> Generator[None, None, None]:
    app.dependency_overrides[get_upload_embedding_service] = (
        lambda: FakeEmbeddingService()
    )
    app.dependency_overrides[get_chat_embedding_service] = (
        lambda: FakeEmbeddingService()
    )
    app.dependency_overrides[get_ollama_client] = lambda: FakeOllamaClient()
    app.dependency_overrides[get_chat_history_service] = lambda: fake_history_service
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
