from fastapi.testclient import TestClient


def test_documents_list_contract(client: TestClient) -> None:
    response = client.get("/documents")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_delete_document_contract(client: TestClient) -> None:
    response = client.delete("/documents/example-file-id")

    assert response.status_code == 200
    assert response.json()["file_id"] == "example-file-id"
    assert isinstance(response.json()["deleted"], bool)


def test_chat_contract(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={
            "question": "What is this document about?",
            "session_id": "test-session",
            "top_k": 3,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["session_id"] == "test-session"
    assert isinstance(payload["answer"], str)
    assert isinstance(payload["sources"], list)


def test_upload_rejects_unsupported_file_type(client: TestClient) -> None:
    response = client.post(
        "/upload",
        files={
            "file": (
                "example.docx",
                b"fake content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Unsupported file type. Only PDF and TXT files are allowed.",
    }


def test_upload_accepts_txt_contract(client: TestClient) -> None:
    response = client.post(
        "/upload",
        files={"file": ("example.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 201

    payload = response.json()

    assert isinstance(payload["file_id"], str)
    assert payload["file_id"]
    assert payload["filename"] == "example.txt"
    assert payload["chunks_indexed"] == 1
    assert payload["status"] == "indexed"


def test_retrieve_contract(client: TestClient) -> None:
    response = client.post(
        "/chat/retrieve",
        json={
            "question": "What is Pipefy?",
            "session_id": "test-session",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_chat_history_contract(client: TestClient) -> None:
    response = client.get("/chat/sessions/test-session/history")

    assert response.status_code == 200

    payload = response.json()

    assert payload["session_id"] == "test-session"
    assert isinstance(payload["messages"], list)


def test_clear_chat_history_contract(client: TestClient) -> None:
    response = client.delete("/chat/sessions/test-session/history")

    assert response.status_code == 200

    payload = response.json()

    assert payload["session_id"] == "test-session"
    assert isinstance(payload["deleted"], bool)
