import pickle
from typing import List
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from discordbot.models.orm.base import Base
from discordbot.models.message import TimeStampedMessage
from discordbot.services.user_context.models.user_context import UserContext

class UserContextORM(Base):
    """ORM for user context."""

    __tablename__ = "user_context"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    user_name: Mapped[str] = mapped_column(String)
    _user_chat_history: Mapped[bytes] = mapped_column(name="user_chat_history")

    def __init__(self, user_id: str, user_name: str, user_chat_history: List[TimeStampedMessage]):
        self.user_id = user_id
        self.user_name = user_name
        self.user_chat_history = user_chat_history

    @classmethod
    def from_user_context(cls, user_context: UserContext):
        return cls(
            user_id=user_context.user_id,
            user_name=user_context.user_name,
            user_chat_history=user_context.user_chat_history,
        )

    def to_user_context(self) -> UserContext:
        return UserContext(
            user_id=self.user_id,
            user_name=self.user_name,
            user_chat_history=self.user_chat_history,
        )

    @property
    def user_chat_history(self) -> List[TimeStampedMessage]:
        if not self._user_chat_history:
            return []
        history_jsons = pickle.loads(self._user_chat_history)
        return [pickle.loads(item) for item in history_jsons]

    @user_chat_history.setter
    def user_chat_history(self, value: List[TimeStampedMessage]):
        history_jsons = [pickle.dumps(item) for item in value]
        self._user_chat_history = pickle.dumps(history_jsons)
