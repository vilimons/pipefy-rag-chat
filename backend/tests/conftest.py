from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.api.routes.upload import get_upload_embedding_service
from app.main import app


class FakeEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        return [0.1] * 384

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]


@pytest.fixture(autouse=True)
def override_embedding_service() -> Generator[None, None, None]:
    app.dependency_overrides[get_upload_embedding_service] = (
        lambda: FakeEmbeddingService()
    )
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
