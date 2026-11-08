from datetime import datetime, timezone

from chatbot_backend.errors import MessageNotFoundError


class MessageStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._messages: dict[int, dict] = {}
        self._next_id = 1

    def create(self, role: str, content: str) -> dict:
        now = datetime.now(timezone.utc)
        message = {
            "id": self._next_id,
            "role": role,
            "content": content,
            "created_at": now,
            "updated_at": now,
        }
        self._messages[message["id"]] = message
        self._next_id += 1
        return message

    def list_messages(self, limit: int, offset: int, role: str | None) -> list[dict]:
        items = [
            m for m in self._messages.values() if role is None or m["role"] == role
        ]
        return items[offset : offset + limit]

    def get(self, message_id: int) -> dict:
        if message_id not in self._messages:
            raise MessageNotFoundError(message_id)
        return self._messages[message_id]

    def update(self, message_id: int, content: str) -> dict:
        message = self.get(message_id)
        message["content"] = content
        message["updated_at"] = datetime.now(timezone.utc)
        return message

    def delete(self, message_id: int) -> None:
        if message_id not in self._messages:
            raise MessageNotFoundError(message_id)
        del self._messages[message_id]


store = MessageStore()