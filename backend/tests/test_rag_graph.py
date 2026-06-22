from typing import Any

from app.core.config import Settings
from app.rag.graph import run_rag_graph
from app.services.chat_history import ChatHistoryService


class FakeEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        return [0.1] * 384


class FakeOllamaClient:
    def generate(self, prompt: str) -> str:
        return "Fake graph answer."


class FakeTracer:
    def trace(
        self,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any],
        function,
    ):
        return function()


class FakeSearchResult:
    docs: list[object] = []


class FakeSearchIndex:
    def info(self) -> dict[str, str]:
        return {"index": "docs"}

    def search(self, query: object, query_params: dict[str, bytes]) -> FakeSearchResult:
        return FakeSearchResult()


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, list[str]] = {}
        self.index = FakeSearchIndex()

    def ft(self, index_name: str) -> FakeSearchIndex:
        return self.index

    def hgetall(self, name: str) -> dict[str, object]:
        return {}

    def scan_iter(self, pattern: str):
        return iter(())

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


def test_rag_graph_returns_fallback_when_no_sources() -> None:
    redis = FakeRedis()
    settings = Settings()
    history_service = ChatHistoryService(
        redis_client=redis,  # type: ignore[arg-type]
        max_messages=6,
    )

    response = run_rag_graph(
        question="What is Pipefy?",
        session_id="test-session",
        top_k=3,
        settings=settings,
        redis_client=redis,  # type: ignore[arg-type]
        embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
        ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
        history_service=history_service,
        tracer=FakeTracer(),  # type: ignore[arg-type]
    )

    assert response.session_id == "test-session"
    assert response.sources == []
    assert "Não encontrei informações relevantes" in response.answer

    history = history_service.get_messages("test-session")

    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"
