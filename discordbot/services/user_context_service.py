from ast import List
from typing import cast
from openai import chat
from sqlalchemy.orm import Session
from hangoutsscheduler.constants import (
    USER_MESSAGE_TYPE,
    SYSTEM_MESSAGE_TYPE,
    AI_MESSAGE_TYPE,
)

from hangoutsscheduler.models.message_context import (
    MessageContext,
    MessageContextChatHistory,
)
from hangoutsscheduler.models.orm.chat_history import ChatHistory, ChatMessage

import logging

logger = logging.getLogger(__name__)


class UserContextService:

    USER_CHAT_HISTORY_NAME = "User Chat"
    USER_CHAT_HISTORY_DESCRIPTION = (
        "Chat history for the specific user across all their channels."
    )

    def _get_or_create_chat_history(
        self, session: Session, username: str
    ) -> ChatHistory:
        chat_history = session.get(ChatHistory, username)
        if chat_history is None:
            chat_history = ChatHistory(username=username, history=[])
            session.add(chat_history)
        return chat_history

    def _update_history(self, chat_history: ChatHistory, new_entry: ChatMessage):
        chat_history.history = (chat_history.history + [new_entry])[
            -8:
        ]  # Keep only the last 8 messages

    def resolve_chat_history(
        self, session: Session, username: str, new_message: ChatMessage
    ) -> MessageContext:
        chat_history = self._get_or_create_chat_history(session, username)
        user_chat_history = MessageContextChatHistory(
            name=self.USER_CHAT_HISTORY_NAME,
            description=self.USER_CHAT_HISTORY_DESCRIPTION,
            messages=chat_history.history[
                :
            ],  # Clone to prevent duplication of new message
        )
        self._update_history(chat_history, new_message)
        session.commit()
        return MessageContext(
            message=new_message.content,
            username=username,
            histories=[user_chat_history],
        )

    def update_with_llm_response(
        self, session: Session, username: str, response: ChatMessage
    ):
        chat_history = self._get_or_create_chat_history(session, username)
        self._update_history(chat_history, response)
        session.commit()
