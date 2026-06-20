from app.services.chat_history import ChatHistoryService


class FakeRedis:
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


def test_chat_history_appends_and_reads_messages() -> None:
    redis = FakeRedis()
    history = ChatHistoryService(
        redis_client=redis,  # type: ignore[arg-type]
        max_messages=6,
    )

    history.append_message(
        session_id="session-1",
        role="user",
        content="Hello",
    )
    history.append_message(
        session_id="session-1",
        role="assistant",
        content="Hi there",
    )

    messages = history.get_messages("session-1")

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there"


def test_chat_history_keeps_only_max_messages() -> None:
    redis = FakeRedis()
    history = ChatHistoryService(
        redis_client=redis,  # type: ignore[arg-type]
        max_messages=3,
    )

    for index in range(5):
        history.append_message(
            session_id="session-1",
            role="user",
            content=f"message-{index}",
        )

    messages = history.get_messages("session-1")

    assert len(messages) == 3
    assert [message.content for message in messages] == [
        "message-2",
        "message-3",
        "message-4",
    ]


def test_chat_history_appends_exchange() -> None:
    redis = FakeRedis()
    history = ChatHistoryService(
        redis_client=redis,  # type: ignore[arg-type]
        max_messages=6,
    )

    history.append_exchange(
        session_id="session-1",
        question="What is Pipefy?",
        answer="Pipefy is a workflow platform.",
    )

    messages = history.get_messages("session-1")

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "What is Pipefy?"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Pipefy is a workflow platform."


def test_chat_history_clear_history_returns_true_when_session_exists() -> None:
    redis = FakeRedis()
    history = ChatHistoryService(
        redis_client=redis,  # type: ignore[arg-type]
        max_messages=6,
    )

    history.append_message(
        session_id="session-1",
        role="user",
        content="Hello",
    )

    deleted = history.clear_history("session-1")

    assert deleted is True
    assert history.get_messages("session-1") == []


def test_chat_history_clear_history_returns_false_when_session_does_not_exist() -> None:
    redis = FakeRedis()
    history = ChatHistoryService(
        redis_client=redis,  # type: ignore[arg-type]
        max_messages=6,
    )

    deleted = history.clear_history("missing-session")

    assert deleted is False
