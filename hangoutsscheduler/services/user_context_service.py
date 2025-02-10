from openai import chat
from sqlalchemy.orm import Session
from hangoutsscheduler.constants import USER_MESSAGE_TYPE, SYSTEM_MESSAGE_TYPE, AI_MESSAGE_TYPE

from hangoutsscheduler.models.meesage_context import MessageContext
from hangoutsscheduler.models.orm.chat_history import ChatHistory

import logging

logger = logging.getLogger(__name__)

class UserContextService:

    def _get_or_create_chat_history(self, session: Session, username: str) -> ChatHistory:
        chat_history = session.get(ChatHistory, username)
        if chat_history is None:
            chat_history = ChatHistory(username=username, history=[])
            session.add(chat_history)
        return chat_history

    def _update_history(self, chat_history: ChatHistory, new_entry: dict):
        chat_history.history = (chat_history.history + [new_entry])[-8:]  # Keep only the last 8 messages

    def resolve_chat_history(self, session: Session, username: str, new_message: str) -> MessageContext:
        chat_history = self._get_or_create_chat_history(session, username)
        self._update_history(chat_history, {"type": USER_MESSAGE_TYPE, "content": new_message})
        session.commit()
        return MessageContext(message=new_message, username=username, history=chat_history.history)

    def update_with_llm_response(self, session: Session, username: str, response: str):
        chat_history = self._get_or_create_chat_history(session, username)
        self._update_history(chat_history, {"type": AI_MESSAGE_TYPE, "content": response})
        session.commit()