import json
from typing import List
from sqlalchemy import ARRAY, String
from sqlalchemy.orm import Mapped, mapped_column

from discordbot.models.orm.base import Base
from discordbot.models.message_context import ChatMessage


class ChatHistory(Base):
    __tablename__ = "chat_history"

    username: Mapped[str] = mapped_column(primary_key=True)
    _history: Mapped[str] = mapped_column(String, name="history")

    def __init__(self, username: str, history: List[ChatMessage]):
        self.username = username
        self.history = history

    @property
    def history(self) -> List[ChatMessage]:
        if not self._history:
            return []

        # Deserialize JSON to list of dictionaries, then convert to ChatMessage objects
        history_dicts = json.loads(self._history)
        return [ChatMessage.from_dict(item) for item in history_dicts]

    @history.setter
    def history(self, value: List[ChatMessage]):
        # Serialize ChatMessage objects to dictionaries, then to JSON
        history_dicts = [msg.to_dict() for msg in value]
        self._history = json.dumps(history_dicts)
