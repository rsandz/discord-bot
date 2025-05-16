from dataclasses import dataclass
from discordbot.models.message import TimeStampedMessage

@dataclass
class UserContext:
    """Represents the context of a user."""

    user_id: str
    """Unique identifier for the user."""

    user_name: str
    """Human readable name for the user."""

    user_chat_history: list[TimeStampedMessage]
    """Chat history for the user."""
    

