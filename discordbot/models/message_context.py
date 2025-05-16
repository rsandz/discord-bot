from dataclasses import dataclass, field
from datetime import datetime as dt
from datetime import timezone
from uuid import uuid4


@dataclass
class ChatMessage:
    """Represents a message in a chat history."""

    type: str
    content: str
    datetime: dt = field(default_factory=lambda: dt.min.replace(tzinfo=timezone.utc))
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert ChatMessage to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "datetime": self.datetime.isoformat() if self.datetime else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        """Create a ChatMessage from a dictionary."""
        # Convert ISO format datetime string back to datetime object if present
        if data.get("datetime") and isinstance(data["datetime"], str):
            data["datetime"] = dt.fromisoformat(data["datetime"])
            # Ensure datetime is timezone-aware
            if data["datetime"].tzinfo is None:
                data["datetime"] = data["datetime"].replace(tzinfo=timezone.utc)

        return cls(**data)


@dataclass
class MessageContextChatHistory:
    """Represents a generic chat history."""

    name: str
    description: str = ""
    messages: list[ChatMessage] = field(default_factory=list)

