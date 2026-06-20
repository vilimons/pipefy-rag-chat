import json
from dataclasses import dataclass
from typing import Literal

from redis import Redis

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


class ChatHistoryService:
    def __init__(
        self,
        redis_client: Redis,
        max_messages: int,
    ) -> None:
        self.redis_client = redis_client
        self.max_messages = max_messages

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        raw_messages = self.redis_client.lrange(
            self._session_key(session_id),
            0,
            -1,
        )

        messages: list[ChatMessage] = []

        for raw_message in raw_messages:
            message_text = (
                raw_message.decode("utf-8")
                if isinstance(raw_message, bytes)
                else str(raw_message)
            )
            payload = json.loads(message_text)

            messages.append(
                ChatMessage(
                    role=payload["role"],
                    content=payload["content"],
                )
            )

        return messages

    def append_message(
        self,
        session_id: str,
        role: Role,
        content: str,
    ) -> None:
        message = json.dumps(
            {
                "role": role,
                "content": content,
            }
        )

        key = self._session_key(session_id)

        self.redis_client.rpush(key, message)
        self.redis_client.ltrim(key, -self.max_messages, -1)

    def append_exchange(
        self,
        session_id: str,
        question: str,
        answer: str,
    ) -> None:
        self.append_message(
            session_id=session_id,
            role="user",
            content=question,
        )
        self.append_message(
            session_id=session_id,
            role="assistant",
            content=answer,
        )

    def clear_history(self, session_id: str) -> bool:
        deleted_count = self.redis_client.delete(self._session_key(session_id))

        return deleted_count > 0

    def _session_key(self, session_id: str) -> str:
        return f"chat:session:{session_id}:messages"
