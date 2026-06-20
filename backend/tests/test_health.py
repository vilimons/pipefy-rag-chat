from fastapi.testclient import TestClient


def test_root_returns_api_metadata(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Pipefy RAG Chat API",
        "docs": "/docs",
        "health": "/health",
    }


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["app"] == "pipefy-rag-chat"
    assert payload["environment"] == "development"
    assert payload["redis"] in {"connected", "disconnected"}
