import json
from typing import List
from sqlalchemy import ARRAY, String
from sqlalchemy.orm import Mapped, mapped_column

from hangoutsscheduler.models.orm.base import Base

class ChatHistory(Base):
    __tablename__ = "chat_history"

    username: Mapped[str] = mapped_column(primary_key=True)
    _history: Mapped[str] = mapped_column(String, name="history")

    def __init__(self, username: str, history: List[str]):
        self.username = username
        self.history = history

    @property
    def history(self) -> List[str]:
        return json.loads(self._history) if self._history else []

    @history.setter
    def history(self, value: List[str]):
        self._history = json.dumps(value)