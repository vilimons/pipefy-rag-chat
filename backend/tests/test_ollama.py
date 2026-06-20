import pytest

from app.services.ollama import OllamaClient, OllamaServiceError


def test_ollama_client_raises_service_error_for_unavailable_service() -> None:
    client = OllamaClient(
        base_url="http://unavailable-ollama",
        model="llama3:8b",
        timeout_seconds=0.001,
    )

    with pytest.raises(OllamaServiceError):
        client.generate("test prompt")


def test_ollama_service_error_message() -> None:
    error = OllamaServiceError("LLM service is unavailable")

    assert str(error) == "LLM service is unavailable"
