from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.api.routes.chat import get_chat_embedding_service, get_ollama_client
from app.api.routes.upload import get_upload_embedding_service
from app.main import app


class FakeEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        return [0.1] * 384

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]


class FakeOllamaClient:
    def generate(self, prompt: str) -> str:
        return "Fake LLM answer based on retrieved context."


@pytest.fixture(autouse=True)
def override_ai_services() -> Generator[None, None, None]:
    app.dependency_overrides[get_upload_embedding_service] = (
        lambda: FakeEmbeddingService()
    )
    app.dependency_overrides[get_chat_embedding_service] = (
        lambda: FakeEmbeddingService()
    )
    app.dependency_overrides[get_ollama_client] = lambda: FakeOllamaClient()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
